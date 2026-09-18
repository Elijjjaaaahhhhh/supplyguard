"""Publish validated historical evaluation and stable forecast BI interfaces."""
import json
import numpy as np
import pandas as pd
from .config import ROOT
from .database import get_connection
from .operations import execute_file, sha256


def publish_bi(connection):
    path = ROOT / 'outputs/final_v3c_predictions.csv'
    digest = sha256(path)
    with connection.transaction():
        execute_file(connection, 38)
        existing = connection.execute('SELECT count(*),min(source_sha256),max(source_sha256) FROM ops.forecast_evaluation').fetchone()
        if existing[0] and existing != (350000, digest, digest):
            raise ValueError('Historical evaluation changed; explicit reviewed migration required')
        if not existing[0]:
            frame = pd.read_csv(path, parse_dates=['dt'])
            keys = ['store_id', 'product_id', 'dt']
            values = ['actual', 'prediction', 'rolling_prediction']
            if len(frame) != 350000 or frame.duplicated(keys).any() or frame[keys+values].isna().any().any():
                raise ValueError('Invalid historical evaluation grain/count/nulls')
            if str(frame.dt.min().date()) != '2024-06-26' or str(frame.dt.max().date()) != '2024-07-02':
                raise ValueError('Unexpected historical evaluation dates')
            if not np.isfinite(frame[values]).all().all() or (frame[values] < 0).any().any():
                raise ValueError('Invalid evaluation values')
            with connection.cursor().copy('COPY ops.forecast_evaluation(store_id,product_id,dt,actual,prediction,rolling_prediction,source_sha256) FROM STDIN') as copy:
                for row in frame[keys+values].itertuples(index=False,name=None):
                    copy.write_row((*row,digest))
        mismatch = connection.execute('''SELECT count(*) FROM ops.forecast_evaluation e
          LEFT JOIN core.fact_daily_demand f USING(store_id,product_id,dt)
          WHERE f.dt IS NULL OR abs(e.actual-f.sale_amount)>1e-7''').fetchone()[0]
        if mismatch:
            raise ValueError(f'Historical evaluation disagrees with observed sales: {mismatch}')
        count,bad = connection.execute('''SELECT count(*),count(*) FILTER(WHERE forecast_date<>as_of_date+1 OR predicted_demand IS NULL)
          FROM mart.bi_forecast_outlook''').fetchone()
        expected = connection.execute('SELECT count(*) FROM mart.control_tower').fetchone()[0]
        if count != expected or bad:
            raise ValueError('Outlook lineage/date/grain failed')
    return {'evaluation_rows':350000,'outlook_rows':count,'evaluation_sha256':digest}


def main():
    with get_connection() as connection:
        print(json.dumps(publish_bi(connection),indent=2))

if __name__ == '__main__':
    main()
