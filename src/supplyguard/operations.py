"""Database stages. The publication transaction owns all decision-table changes."""
import hashlib
import logging
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from psycopg import sql
from .config import ROOT

def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def execute_file(connection, number):
    paths = list((ROOT / 'sql').glob(f'{number:03d}_*.sql'))
    if len(paths) != 1:
        raise ValueError(f'Expected one SQL script numbered {number}')
    text = paths[0].read_text(encoding='utf-8-sig')
    # The caller owns the transaction, including scripts originally used in psql.
    text = re.sub(r'^\s*(BEGIN|COMMIT);\s*$', '', text, flags=re.M)
    if number == 23:
        # Existing V3 and BI views depend on V2. Preserve those dependencies on rerun.
        text = re.sub(r'^DROP VIEW[^;]+;\s*', '', text, flags=re.M)
        text = text.replace('CREATE VIEW ', 'CREATE OR REPLACE VIEW ')
    connection.execute(text)

def bootstrap(connection):
    with connection.transaction():
        for schema in ('raw','staging','core','mart'):
            connection.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
        for n in (1,2,3,5,6,8,10,18,19,26,27):
            execute_file(connection,n)
        execute_file(connection,36)

def ingest_sources(connection):
    from .ingestion.retail import ingest_parquet
    results = {}
    for name in ('train.parquet','eval.parquet'):
        logging.getLogger(__name__).info('Verifying source %s',name)
        path = ROOT / 'data/external' / name
        if not path.is_file():
            raise FileNotFoundError(f'Required source file missing: {path}')
        rows = pq.ParquetFile(path).metadata.num_rows
        digest = sha256(path)
        registered = connection.execute('SELECT sha256,row_count FROM ops.source_file WHERE name=%s',(name,)).fetchone()
        if registered and registered != (digest,rows):
            raise ValueError(f'{name} changed since ingestion; use an explicit source migration')
        existing = connection.execute('SELECT count(*) FROM raw.retail_daily WHERE source_file=%s',(name,)).fetchone()[0]
        if existing == 0:
            ingest_parquet(path)
        elif existing != rows:
            raise ValueError(f'{name}: raw count {existing} differs from file count {rows}')
        if not registered and existing:
            logging.getLogger(__name__).info('Comparing existing raw rows against %s before first registration',name)
            # One-time adoption gate: compare source and raw rows before registering a digest.
            from .ingestion.retail import SOURCE_COLUMNS
            column_list = sql.SQL(',').join(map(sql.Identifier,SOURCE_COLUMNS))
            with connection.transaction():
                connection.execute('CREATE TEMP TABLE source_adoption (LIKE raw.retail_daily INCLUDING DEFAULTS) ON COMMIT DROP')
                copied=0
                with connection.cursor().copy(sql.SQL('COPY source_adoption ({},source_file) FROM STDIN').format(column_list)) as copy:
                    for batch in pq.ParquetFile(path).iter_batches(batch_size=10000,columns=SOURCE_COLUMNS):
                        values=batch.to_pydict()
                        for i in range(batch.num_rows):
                            copy.write_row([values[c][i] for c in SOURCE_COLUMNS]+[name])
                        copied+=batch.num_rows
                        if copied % 250000 == 0:
                            logging.getLogger(__name__).info('Source comparison staged %s/%s rows for %s',copied,rows,name)
                difference=connection.execute(sql.SQL('SELECT EXISTS ((SELECT {} FROM raw.retail_daily WHERE source_file=%s EXCEPT ALL SELECT {} FROM source_adoption) UNION ALL (SELECT {} FROM source_adoption EXCEPT ALL SELECT {} FROM raw.retail_daily WHERE source_file=%s))').format(column_list,column_list,column_list,column_list),(name,name)).fetchone()[0]
                if difference:
                    raise ValueError(f'{name}: existing raw contents do not match the source file')
        connection.execute('INSERT INTO ops.source_file(name,sha256,row_count) VALUES(%s,%s,%s) ON CONFLICT(name) DO NOTHING',(name,digest,rows))
        results[name]={'rows':rows,'sha256':digest,'action':'reused' if existing else 'loaded'}
    return results

def warehouse(connection):
    with connection.transaction():
        bad_arrays=connection.execute('''SELECT count(*) FROM raw.retail_daily
            WHERE hours_sale IS NULL OR hours_stock_status IS NULL
            OR cardinality(hours_sale)<>24 OR cardinality(hours_stock_status)<>24''').fetchone()[0]
        if bad_arrays:
            raise ValueError(f'Hourly source array shape gate failed for {bad_arrays} rows')
        execute_file(connection,11)
        execute_file(connection,37)
        ambiguous_city=connection.execute('SELECT count(*) FROM (SELECT store_id FROM staging.retail_daily GROUP BY store_id HAVING count(DISTINCT city_id)>1) s').fetchone()[0]
        if ambiguous_city:
            raise ValueError('A store maps to multiple cities; explicit location history is required')
        connection.execute('TRUNCATE feature.daily_demand')
        for n in range(20,26):
            execute_file(connection,n)
        expected=connection.execute('SELECT count(*) FROM raw.retail_daily').fetchone()[0]
        for table in ('staging.retail_daily','core.fact_daily_demand','feature.daily_demand'):
            actual=connection.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(*table.split('.')))).fetchone()[0]
            if actual != expected or actual == 0:
                raise ValueError(f'{table} row count failed: {actual}, expected {expected}')
        invalid=connection.execute('SELECT count(*) FROM core.fact_daily_demand WHERE sale_amount < 0 OR sale_amount >= %s::float8 OR stockout_hours NOT BETWEEN 0 AND 16',('Infinity',)).fetchone()[0]
        if invalid:
            raise ValueError('Invalid core demand values')
        mixed=connection.execute('SELECT count(*) FROM core.dim_store WHERE management_group_id=-1').fetchone()[0]
    return {'rows':expected,'mixed_management_group_stores':mixed}

def copy_frame(connection,table,frame):
    columns=list(frame.columns)
    schema,name=table.split('.')
    integers={r[0] for r in connection.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s AND data_type IN ('smallint','integer','bigint')",(schema,name)).fetchall()}
    statement=sql.SQL('COPY {} ({}) FROM STDIN').format(sql.Identifier(*table.split('.')),sql.SQL(',').join(map(sql.Identifier,columns)))
    with connection.cursor().copy(statement) as copy:
        for row in frame.itertuples(index=False,name=None):
            values=[]
            for column,value in zip(columns,row):
                if pd.isna(value):
                    value=None
                elif column in integers:
                    if int(value)!=value:
                        raise ValueError(f'Nonintegral scenario input: {column}')
                    value=int(value)
                elif isinstance(value,np.generic):
                    value=value.item()
                values.append(value)
            copy.write_row(values)

def ensure_scenario(connection,settings,as_of,regenerate):
    from .scenario import generate_inputs as generator
    count,low,high=connection.execute('SELECT count(*),min(as_of_date),max(as_of_date) FROM scenario.inventory_position').fetchone()
    if count and not regenerate:
        if count != settings.sample_size or low != as_of or high != as_of:
            raise ValueError('Existing scenario size/date differs; select matching settings or --regenerate-scenario')
        return 'reused'
    generator.RANDOM_SEED=settings.random_seed
    generator.SAMPLE_SIZE=settings.sample_size
    generator.AS_OF_DATE=pd.Timestamp(as_of)
    # Stable row order is necessary for reproducible sampling and random assignments.
    rows=connection.execute("SELECT store_id,product_id,avg(sale_amount) mean_daily_demand,stddev_samp(sale_amount) demand_std,max(sale_amount) max_daily_demand,avg(stockout_hours) avg_stockout_hours,count(*) FILTER(WHERE sale_amount=0)::float8/count(*) zero_sales_fraction FROM core.fact_daily_demand WHERE source_file='train.parquet' AND dt<=%s GROUP BY store_id,product_id ORDER BY store_id,product_id",(as_of,))
    profiles=pd.DataFrame(rows.fetchall(),columns=[d.name for d in rows.description])
    # Honour arbitrary sample sizes without the original fixed 250/250/500 assumption.
    profiles['cv']=profiles.demand_std / profiles.mean_daily_demand.replace(0,np.nan)
    quarter=settings.sample_size//4
    high_volume=profiles.sort_values(['mean_daily_demand','store_id','product_id'],ascending=[False,True,True]).head(quarter)
    remaining=profiles.drop(high_volume.index)
    high_variance=remaining.sort_values(['cv','store_id','product_id'],ascending=[False,True,True]).head(quarter)
    remaining=remaining.drop(high_variance.index)
    selected=pd.concat([high_volume,high_variance,remaining.sample(n=settings.sample_size-len(high_volume)-len(high_variance),random_state=settings.random_seed)],ignore_index=True)
    rng=np.random.default_rng(settings.random_seed)
    frames=[generator.generate_inventory_positions(selected,rng),generator.generate_supplier_policies(selected,rng),generator.generate_product_priorities(selected,rng)]
    connection.execute('TRUNCATE scenario.inventory_position,scenario.supplier_policy,scenario.product_priority')
    for name,frame in zip(('inventory_position','supplier_policy','product_priority'),frames):
        copy_frame(connection,'scenario.'+name,frame)
    return 'generated'

def check_publication(connection,settings,run_id):
    count,budget=connection.execute('SELECT count(*),coalesce(sum(allocated_order_value),0) FROM mart.control_tower').fetchone()
    if count != settings.sample_size:
        raise ValueError(f'Control tower has {count} rows, expected {settings.sample_size}')
    if budget > settings.budget + 1e-6 or budget < 0:
        raise ValueError('Shared budget gate failed')
    bad=connection.execute('''SELECT count(*) FROM mart.control_tower c JOIN mart.order_recommendation r USING(store_id,product_id,decision_date)
        WHERE c.allocated_quantity<0 OR c.allocated_order_value<0
        OR c.allocated_quantity>r.final_recommended_quantity+1e-8
        OR (c.allocated_quantity>0 AND (c.allocated_quantity+1e-8<r.minimum_order_quantity
        OR abs(c.allocated_quantity/r.case_pack_size-round(c.allocated_quantity/r.case_pack_size))>1e-8))
        OR (c.reorder_required AND r.final_recommended_quantity<=0 AND c.control_tower_status<>'CONSTRAINED - ESCALATE')
        OR abs(c.allocated_order_value-c.allocated_quantity*r.supplier_unit_cost)>1e-6''').fetchone()[0]
    if bad:
        raise ValueError(f'Procurement validity gate failed for {bad} rows')
    lineage=connection.execute('''SELECT count(*) FROM mart.control_tower c JOIN ops.forecast f
        ON f.run_id=c.forecast_run_id AND f.store_id=c.store_id AND f.product_id=c.product_id
        AND f.target_date=c.forecast_target_date
        WHERE c.forecast_run_id=%s AND c.model_id=f.model_id
        AND abs(c.expected_daily_demand-greatest(f.prediction,0.01))<1e-8''',(run_id,)).fetchone()[0]
    if lineage != count:
        raise ValueError('Forecast lineage gate failed')
    return {'control_tower_rows':count,'allocated_capital':float(budget),'budget':settings.budget,'forecast_lineage_rows':lineage}

def publish(connection,settings,as_of,run_id,model_id,regenerate=False):
    with connection.transaction():
        for name,value in {'as_of_date':str(as_of),'run_id':str(run_id),'budget':settings.budget,**{'weight_'+k:v for k,v in settings.weights.items()}}.items():
            connection.execute('SELECT set_config(%s,%s,true)',('supplyguard.'+name,str(value)))
        scenario_action=ensure_scenario(connection,settings,as_of,regenerate)
        for n in (28,29,30,32,33,34):
            execute_file(connection,n)
        for table in ('mart.inventory_decision','mart.control_tower'):
            connection.execute(sql.SQL('ALTER TABLE {} ADD COLUMN IF NOT EXISTS forecast_run_id UUID, ADD COLUMN IF NOT EXISTS model_id TEXT, ADD COLUMN IF NOT EXISTS forecast_target_date DATE').format(sql.Identifier(*table.split('.'))))
            connection.execute(sql.SQL('UPDATE {} SET forecast_run_id=%s,model_id=%s,forecast_target_date=%s::date+1').format(sql.Identifier(*table.split('.'))),(run_id,model_id,as_of))
        connection.execute('''CREATE OR REPLACE VIEW mart.bi_pipeline_status AS
            SELECT r.run_id,r.as_of_date,r.model_id,r.started_at,r.finished_at,r.status,
            r.summary, r.config->>'budget' AS scenario_budget FROM ops.pipeline_run r
            WHERE r.status='success' ORDER BY r.finished_at DESC LIMIT 1''')
        from .bi import publish_bi
        publish_bi(connection)
        summary=check_publication(connection,settings,run_id)
        summary['scenario_action']=scenario_action
        from psycopg.types.json import Jsonb
        # Success metadata commits with the published marts, never ahead of them.
        connection.execute("UPDATE ops.pipeline_run SET status='success',finished_at=now(),summary=%s,model_id=%s WHERE run_id=%s",(Jsonb(summary),model_id,run_id))
    return summary
