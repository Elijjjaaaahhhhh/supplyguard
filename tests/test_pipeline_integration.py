"""Opt-in PostgreSQL checks. Every mutation is rolled back."""
import os
from dataclasses import replace
import pytest
from dotenv import load_dotenv
from supplyguard.config import ROOT,load_settings
from supplyguard.database import get_connection
from supplyguard import operations

pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.getenv('SUPPLYGUARD_DB_TESTS')!='1',reason='Set SUPPLYGUARD_DB_TESTS=1 for rollback-only database tests')]

@pytest.fixture
def database():
    load_dotenv(ROOT/'.env')
    with get_connection() as connection:
        with connection.transaction(force_rollback=True):
            connection.execute('SELECT pg_advisory_xact_lock(839104291)')
            yield connection

def latest(connection):
    result=connection.execute("SELECT run_id,as_of_date,model_id FROM ops.pipeline_run WHERE status='success' ORDER BY finished_at DESC LIMIT 1").fetchone()
    assert result, 'Run the operational pipeline successfully before integration tests'
    return result

def snapshot(connection):
    return connection.execute("SELECT md5(string_agg(row_to_json(c)::text,',' ORDER BY store_id,product_id)) FROM mart.control_tower c").fetchone()[0]

def test_zero_budget_never_funds_orders(database):
    run_id,as_of,model_id=latest(database)
    summary=operations.publish(database,replace(load_settings(),budget=0),as_of,run_id,model_id)
    assert summary['allocated_capital']==0
    assert database.execute('SELECT count(*) FROM mart.control_tower WHERE allocated_quantity>0').fetchone()[0]==0

@pytest.mark.parametrize('budget',[100,5000])
def test_small_budgets_preserve_procurement_rules(database,budget):
    run_id,as_of,model_id=latest(database)
    summary=operations.publish(database,replace(load_settings(),budget=budget),as_of,run_id,model_id)
    assert 0<=summary['allocated_capital']<=budget+1e-6

def test_failed_publication_preserves_previous_snapshot(database,monkeypatch):
    run_id,as_of,model_id=latest(database)
    before=snapshot(database)
    def fail(*args):
        raise ValueError('injected quality failure')
    monkeypatch.setattr(operations,'check_publication',fail)
    with pytest.raises(ValueError,match='injected'):
        operations.publish(database,load_settings(),as_of,run_id,model_id)
    assert snapshot(database)==before

def test_invalid_allocation_detected(database):
    run_id,_,_=latest(database)
    database.execute('UPDATE mart.control_tower SET allocated_quantity=-1 WHERE (store_id,product_id)=(SELECT store_id,product_id FROM mart.control_tower LIMIT 1)')
    with pytest.raises(ValueError,match='Procurement'):
        operations.check_publication(database,load_settings(),run_id)

def test_moq_cap_is_treated_as_physical_block(database):
    run_id,as_of,_=latest(database)
    database.execute("SELECT set_config('supplyguard.as_of_date',%s,true)",(str(as_of),))
    database.execute("SELECT set_config('supplyguard.run_id',%s,true)",(str(run_id),))
    database.execute('UPDATE mart.inventory_decision SET reorder_required=true,raw_order_quantity=100,minimum_order_quantity=12,case_pack_size=6,warehouse_capacity_remaining=6,working_capital_limit=100000,shelf_life_days=NULL')
    operations.execute_file(database,29)
    assert database.execute('SELECT max(final_recommended_quantity) FROM mart.order_recommendation').fetchone()[0]==0

def test_forward_features_match_existing_sql_at_historical_target(database):
    from datetime import date
    import pandas as pd
    from supplyguard.forecasting import build_forward_features
    pair=database.execute('SELECT store_id,product_id FROM core.fact_daily_demand ORDER BY store_id,product_id LIMIT 1').fetchone()
    cursor=database.execute('SELECT f.*,p.first_category_id,p.second_category_id,p.third_category_id FROM core.fact_daily_demand f JOIN core.dim_product p USING(product_id) WHERE f.store_id=%s AND f.product_id=%s AND dt BETWEEN %s AND %s ORDER BY dt',(*pair,date(2024,6,4),date(2024,7,1)))
    history=pd.DataFrame(cursor.fetchall(),columns=[d.name for d in cursor.description])
    row=build_forward_features(history,date(2024,7,1)).iloc[0]
    columns=['sales_lag_1','sales_lag_2','sales_lag_3','sales_lag_7','sales_lag_14','sales_rolling_mean_7','sales_rolling_mean_14','sales_rolling_mean_28','sales_rolling_std_7','sales_rolling_std_14','sales_rolling_std_28','sales_rolling_max_7','sales_rolling_max_14','sales_rolling_max_28','recent_growth_7_vs_28','stockout_lag_1','stockout_rolling_mean_7']
    expected=database.execute('SELECT '+','.join(columns)+' FROM feature.v_demand_model_v3 WHERE store_id=%s AND product_id=%s AND dt=%s',(*pair,date(2024,7,2))).fetchone()
    assert expected is not None
    assert row[columns].to_numpy(dtype=float)==pytest.approx(expected)

def test_concurrent_pipeline_lock_is_rejected(database):
    with get_connection() as other:
        assert other.execute('SELECT pg_try_advisory_lock(839104291)').fetchone()[0] is False

def test_regenerated_scenario_handles_nullable_integers_and_is_repeatable(database):
    _,as_of,_=latest(database)
    settings=replace(load_settings(),sample_size=20)
    operations.ensure_scenario(database,settings,as_of,True)
    first=database.execute('SELECT store_id,product_id,shelf_life_days FROM scenario.product_priority ORDER BY store_id,product_id').fetchall()
    assert len(first)==20
    operations.ensure_scenario(database,settings,as_of,True)
    assert database.execute('SELECT store_id,product_id,shelf_life_days FROM scenario.product_priority ORDER BY store_id,product_id').fetchall()==first

def test_multi_group_stores_are_explicit_and_associations_preserved(database):
    assert database.execute('''SELECT count(*) FROM core.dim_store d
        JOIN (SELECT store_id,count(*) n FROM core.bridge_store_management_group GROUP BY store_id) b USING(store_id)
        WHERE b.n>1 AND d.management_group_id<>-1''').fetchone()[0]==0
    assert database.execute('''SELECT count(*) FROM (SELECT DISTINCT store_id,management_group_id FROM staging.retail_daily
        EXCEPT SELECT store_id,management_group_id FROM core.bridge_store_management_group) missing''').fetchone()[0]==0

def test_republication_is_deterministic(database):
    run_id,as_of,model_id=latest(database)
    query='SELECT store_id,product_id,expected_daily_demand,raw_order_quantity,final_recommended_quantity,allocated_quantity,allocated_order_value,control_tower_status FROM mart.control_tower ORDER BY store_id,product_id'
    before=database.execute(query).fetchall()
    operations.publish(database,load_settings(),as_of,run_id,model_id)
    assert database.execute(query).fetchall()==before

def test_registered_model_reused_without_refitting(database,monkeypatch):
    from supplyguard.forecasting import fit_or_load,HistGradientBoostingRegressor
    _,as_of,expected_model_id=latest(database)
    def unexpected_fit(*args,**kwargs):
        raise AssertionError('Matching registered model should be reused')
    monkeypatch.setattr(HistGradientBoostingRegressor,'fit',unexpected_fit)
    model,model_id,details=fit_or_load(database,load_settings(),as_of)
    assert model_id==expected_model_id
    assert details['action']=='reused'
    assert model.n_features_in_==27
