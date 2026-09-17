"""Versioned V3C fitting and genuinely forward, next-day feature construction."""
from datetime import timedelta
import gc
import hashlib
import json
import os
import platform
import uuid
import joblib
import numpy as np
import pandas as pd
import sklearn
from psycopg.types.json import Jsonb
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
from .config import ROOT
from .models.final_evaluation import FEATURE_COLUMNS
from .operations import sha256

MODEL_PARAMETERS=dict(loss='squared_error',learning_rate=.1,max_iter=100,max_leaf_nodes=31,l2_regularization=1.,random_state=42)

def frame_query(connection,query,params=()):
    # Named server cursor bounds temporary Python object memory while reading millions of rows.
    chunks=[]
    with connection.transaction():
        with connection.cursor(name='read_'+uuid.uuid4().hex) as cursor:
            cursor.execute(query,params)
            while rows:=cursor.fetchmany(50000):
                frame=pd.DataFrame(rows,columns=[d.name for d in cursor.description])
                for column in frame.select_dtypes(include=['float64']).columns:
                    frame[column]=frame[column].astype('float32')
                chunks.append(frame)
    if not chunks:
        raise ValueError('No eligible rows for forecasting')
    return pd.concat(chunks,ignore_index=True)

def training_frame(connection,as_of):
    columns=','.join(['target_sale_amount',*FEATURE_COLUMNS])
    frame=frame_query(connection,f'SELECT {columns} FROM feature.v_demand_model_v3 WHERE dt<=%s AND history_count_28=28 ORDER BY store_id,product_id,dt',(as_of,))
    frame['is_weekend']=frame.is_weekend.astype('int8')
    if not np.isfinite(frame.to_numpy(dtype=float)).all() or (frame.target_sale_amount<0).any():
        raise ValueError('Training inputs contain missing, nonfinite, or invalid target values')
    return frame

def fit_or_load(connection,settings,as_of,retrain=False):
    frame=training_frame(connection,as_of)
    data_digest=hashlib.sha256(pd.util.hash_pandas_object(frame,index=False).values.tobytes()).hexdigest()
    parameters={**MODEL_PARAMETERS,'random_state':settings.random_seed}
    identity={'data_sha256':data_digest,'features':FEATURE_COLUMNS,'parameters':parameters,'trained_through':str(as_of),'sklearn':sklearn.__version__,'numpy':np.__version__,'python':platform.python_version(),'implementation_sha256':sha256(__file__),'model_threads':settings.model_threads}
    model_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
    if retrain:
        model_id+='-'+uuid.uuid4().hex[:8]
    directory=ROOT/settings.artifact_dir/'models'/model_id
    model_path=directory/'model.joblib'
    registered=connection.execute('SELECT artifact_sha256,manifest FROM ops.model_artifact WHERE model_id=%s',(model_id,)).fetchone()
    if registered:
        if not model_path.exists() or sha256(model_path)!=registered[0]:
            raise ValueError('Registered model artifact is missing or changed; use --retrain')
        model=joblib.load(model_path)
        del frame
        gc.collect()
        return model,model_id,{'action':'reused',**registered[1]}
    model=HistGradientBoostingRegressor(**parameters)
    with threadpool_limits(limits=settings.model_threads):
        model.fit(frame[FEATURE_COLUMNS],frame.target_sale_amount.to_numpy())
    manifest={**identity,'model_id':model_id,'training_rows':len(frame),'purpose':'operational_next_day; historical holdout results unchanged'}
    directory.mkdir(parents=True,exist_ok=True)
    temporary=directory/'model.joblib.tmp'
    joblib.dump(model,temporary,compress=3)
    os.replace(temporary,model_path)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    connection.execute('INSERT INTO ops.model_artifact(model_id,trained_through,artifact_path,artifact_sha256,manifest) VALUES(%s,%s,%s,%s,%s)',(model_id,as_of,str(model_path.relative_to(ROOT)),sha256(model_path),Jsonb(manifest)))
    del frame
    gc.collect()
    return model,model_id,{'action':'trained',**manifest}

def build_forward_features(history,as_of,holiday_flag=0):
    """History ends at cutoff; target-day sales are never required or read."""
    history=history.copy()
    history['dt']=pd.to_datetime(history.dt)
    cutoff=pd.Timestamp(as_of)
    history=history.loc[history.dt.between(cutoff-pd.Timedelta(days=27),cutoff)].sort_values(['store_id','product_id','dt'])
    key=['store_id','product_id']
    if history.duplicated(key+['dt']).any():
        raise ValueError('Duplicate daily observations in forward history')
    group=history.groupby(key,sort=True)
    if history.empty or (group.size()!=28).any():
        raise ValueError('Every scored series requires 28 consecutive days through the cutoff')
    records=[]
    target=cutoff+pd.Timedelta(days=1)
    for (store,product),part in group:
        last=part.iloc[-1]
        sales=part.sale_amount.to_numpy(dtype=float)
        stocks=part.stockout_hours.to_numpy(dtype=float)
        record={'store_id':store,'product_id':product,
            **{c:last[c] for c in ('first_category_id','second_category_id','third_category_id')},
            'day_of_week':target.isoweekday(),'is_weekend':int(target.isoweekday()>=6),
            'holiday_flag':holiday_flag,'discount':last.discount,'activity_flag':last.activity_flag,
            'stockout_lag_1':stocks[-1],'stockout_rolling_mean_7':stocks[-7:].mean()}
        for lag in (1,2,3,7,14):
            record[f'sales_lag_{lag}']=sales[-lag]
        for window in (7,14,28):
            record[f'sales_rolling_mean_{window}']=sales[-window:].mean()
            record[f'sales_rolling_std_{window}']=sales[-window:].std(ddof=1)
            record[f'sales_rolling_max_{window}']=sales[-window:].max()
        record['recent_growth_7_vs_28']=sales[-7:].mean()-sales.mean()
        records.append(record)
    result=pd.DataFrame(records)[FEATURE_COLUMNS]
    if not np.isfinite(result.to_numpy(dtype=float)).all():
        raise ValueError('Nonfinite forward inputs')
    return result

def score(connection,model,model_id,settings,as_of,run_id):
    history=frame_query(connection,'''SELECT f.store_id,f.product_id,f.dt,f.sale_amount,f.stockout_hours,
        f.discount,f.activity_flag,p.first_category_id,p.second_category_id,p.third_category_id
        FROM core.fact_daily_demand f JOIN core.dim_product p USING(product_id)
        WHERE f.dt BETWEEN %s::date-27 AND %s::date ORDER BY f.store_id,f.product_id,f.dt''',(as_of,as_of))
    expected=connection.execute('SELECT count(*) FROM (SELECT DISTINCT store_id,product_id FROM core.fact_daily_demand WHERE dt<=%s) s',(as_of,)).fetchone()[0]
    features=build_forward_features(history,as_of,settings.future_holiday_flag)
    if len(features)!=expected:
        raise ValueError('Forward scoring does not cover all historical series')
    with threadpool_limits(limits=settings.model_threads):
        predictions=np.clip(model.predict(features),0,None)
    if not np.isfinite(predictions).all():
        raise ValueError('Nonfinite predictions')
    policy=f'commercial=carry_forward;holiday={settings.future_holiday_flag};one_day_level_for_inventory'
    with connection.transaction():
        with connection.cursor().copy('COPY ops.forecast(run_id,store_id,product_id,as_of_date,target_date,model_id,prediction,input_policy) FROM STDIN') as copy:
            for row,prediction in zip(features[['store_id','product_id']].itertuples(index=False),predictions):
                copy.write_row((run_id,int(row.store_id),int(row.product_id),as_of,as_of+timedelta(days=1),model_id,float(prediction),policy))
    return {'forecast_rows':len(features),'as_of_date':str(as_of),'target_date':str(as_of+timedelta(days=1)),'input_policy':policy}
