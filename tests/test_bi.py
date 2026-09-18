"""Opt-in Phase 10 contracts against the published database snapshot."""
import os
import pytest
from supplyguard.database import get_connection
pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.getenv('SUPPLYGUARD_DB_TESTS')!='1',reason='Requires published PostgreSQL snapshot')]

def test_bi_outlook_matches_exact_published_forecast():
    with get_connection() as c:
        assert c.execute('''SELECT count(*) FROM mart.bi_forecast_outlook b FULL JOIN mart.control_tower t USING(store_id,product_id)
          WHERE b.store_id IS NULL OR t.store_id IS NULL OR b.forecast_run_id<>t.forecast_run_id::text
          OR b.forecast_date<>t.forecast_target_date OR b.forecast_date<>b.as_of_date+1
          OR abs(greatest(b.predicted_demand,0.01)-t.expected_daily_demand)>1e-8''').fetchone()[0]==0
        assert c.execute('SELECT count(*)=count(DISTINCT(store_id,product_id,forecast_date)) FROM mart.bi_forecast_outlook').fetchone()[0]

def test_holdout_remains_distinct_from_operational_forecast():
    with get_connection() as c:
        rows,low,high,mae,rmse,wape=c.execute('''SELECT count(*),min(dt)::text,max(dt)::text,avg(abs(actual-prediction)),sqrt(avg(power(actual-prediction,2))),sum(abs(actual-prediction))/sum(actual) FROM mart.bi_forecast_evaluation''').fetchone()
        assert (rows,low,high)==(350000,'2024-06-26','2024-07-02')
        assert (mae,rmse,wape)==pytest.approx((0.3815378896692485,0.693255797098157,0.31979963533850225))
        assert c.execute('SELECT count(*) FROM mart.bi_forecast_evaluation WHERE dt>DATE \'2024-07-02\'').fetchone()[0]==0

def test_observed_history_grain_and_cutoff():
    with get_connection() as c:
        assert c.execute('SELECT count(*)=count(DISTINCT(store_id,product_id,dt)) FROM mart.bi_demand_history').fetchone()[0]
        assert c.execute('''SELECT count(*) FROM mart.bi_demand_history h JOIN mart.control_tower t USING(store_id,product_id) WHERE h.dt>t.decision_date''').fetchone()[0]==0
