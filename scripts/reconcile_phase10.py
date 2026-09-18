from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
from supplyguard.database import get_connection
from supplyguard.config import ROOT
from supplyguard.forecasting import build_forward_features
from threadpoolctl import threadpool_limits
from pathlib import Path
import json,math,joblib,pandas as pd
c=get_connection()
# One read-only consistent snapshot for the reconciliation evidence.
c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
clauses={'healthy':"control_tower_status='HEALTHY'",'watch':"control_tower_status='WATCH'",'critical':"urgency_band='CRITICAL'",'constrained':"control_tower_status='CONSTRAINED - ESCALATE'",'funded':"allocated_quantity>0",'unfunded':"control_tower_status='REORDER - UNFUNDED'"}
records={}
for name,clause in clauses.items():
 q=c.execute('SELECT * FROM mart.bi_forecast_outlook WHERE '+clause+' ORDER BY store_id,product_id LIMIT 1')
 row=q.fetchone();assert row, name
 b=dict(zip([x.name for x in q.description],row));key=(b['store_id'],b['product_id'])
 source_inventory=c.execute('SELECT on_hand_quantity,on_order_quantity,backorder_quantity FROM scenario.inventory_position WHERE store_id=%s AND product_id=%s',key).fetchone()
 assert all(abs(b[k]-v)<1e-8 for k,v in zip(['on_hand_quantity','on_order_quantity','backorder_quantity'],source_inventory))
 assert abs(b['average_lead_time_days']-c.execute('SELECT average_lead_time_days FROM scenario.supplier_policy WHERE store_id=%s AND product_id=%s',key).fetchone()[0])<1e-8
 assert abs(b['final_recommended_quantity']-c.execute('SELECT final_recommended_quantity FROM mart.order_recommendation WHERE store_id=%s AND product_id=%s',key).fetchone()[0])<1e-8
 funding=c.execute('SELECT allocated_quantity FROM mart.procurement_capital_allocation WHERE store_id=%s AND product_id=%s',key).fetchone()
 assert abs(b['allocated_quantity']-(funding[0] if funding else 0))<1e-8
 q=c.execute('SELECT * FROM mart.inventory_decision WHERE store_id=%s AND product_id=%s',key);d=dict(zip([x.name for x in q.description],q.fetchone()))
 q=c.execute('SELECT dt,sale_amount,stockout_hours FROM mart.bi_demand_history WHERE store_id=%s AND product_id=%s ORDER BY dt',key)
 history=[dict(zip([x.name for x in q.description],r)) for r in q.fetchall()]
 q=c.execute('SELECT dt,actual,prediction,rolling_prediction FROM mart.bi_forecast_evaluation WHERE store_id=%s AND product_id=%s ORDER BY dt',key)
 evaluation=[dict(zip([x.name for x in q.description],r)) for r in q.fetchall()]
 assert len(history)==97 and len(evaluation)==7
 for e in evaluation:
  assert abs(e['actual']-next(h['sale_amount'] for h in history if h['dt']==e['dt']))<1e-8
  prior=[h['sale_amount'] for h in history if h['dt']<e['dt']][-7:]
  assert abs(sum(prior)/7-e['rolling_prediction'])<1e-7
 q=c.execute('''SELECT f.*,p.first_category_id,p.second_category_id,p.third_category_id FROM core.fact_daily_demand f JOIN core.dim_product p USING(product_id)
 WHERE store_id=%s AND product_id=%s AND dt BETWEEN %s::date-27 AND %s::date ORDER BY dt''',(*key,b['as_of_date'],b['as_of_date']))
 frame=pd.DataFrame(q.fetchall(),columns=[x.name for x in q.description])
 artifact,manifest=c.execute('SELECT artifact_path,manifest FROM ops.model_artifact WHERE model_id=%s',(b['model_id'],)).fetchone()
 for column in frame.select_dtypes(include=['float64']).columns:
  frame[column]=frame[column].astype('float32')
 model=joblib.load(ROOT/artifact)
 holiday=c.execute("SELECT (config->>'future_holiday_flag')::int FROM ops.pipeline_run WHERE run_id=%s",(b['forecast_run_id'],)).fetchone()[0]
 features=build_forward_features(frame,b['as_of_date'],holiday)
 with threadpool_limits(limits=4): prediction=max(float(model.predict(features)[0]),0)
 assert abs(prediction-b['predicted_demand'])<1e-8
 assert abs(b['inventory_position']-(b['on_hand_quantity']+b['on_order_quantity']-b['backorder_quantity']))<1e-8
 mu=max(prediction,0.01);z=2.326 if d['target_service_level']>=.99 else 1.96 if d['target_service_level']>=.975 else 1.645
 ss=z*math.sqrt(d['average_lead_time_days']*d['demand_std']**2+mu**2*d['lead_time_std_days']**2)
 assert abs(ss-b['safety_stock'])<1e-7
 assert abs(b['reorder_point']-(mu*b['average_lead_time_days']+ss))<1e-7
 assert abs(b['days_of_supply']-b['on_hand_quantity']/mu)<1e-7
 assert abs(b['coverage_gap_days']-max(b['average_lead_time_days']-b['days_of_supply'],0))<1e-7
 assert abs(b['raw_order_quantity']-max(mu*d['planning_horizon_days']+ss-b['inventory_position'],0))<1e-7
 if b['allocated_quantity']>0:
  assert b['allocated_quantity']>=b['minimum_order_quantity'] and b['allocated_quantity']<=b['final_recommended_quantity']
  assert abs(b['allocated_quantity']/b['case_pack_size']-round(b['allocated_quantity']/b['case_pack_size']))<1e-8
 records[name]={'outlook':b,'history':history,'evaluation':evaluation,'recomputed_model_prediction':prediction,'math_checks':'PASS'}
q=c.execute('SELECT count(*) AS series,sum(allocated_order_value) AS allocated_capital,sum(allocated_quantity) AS funded_quantity,count(*) FILTER(WHERE allocated_quantity>0) AS funded_orders,count(*) FILTER(WHERE capital_constrained) AS capital_constrained,count(*) FILTER(WHERE capacity_constrained) AS capacity_constrained,count(*) FILTER(WHERE shelf_life_constrained) AS shelf_life_constrained FROM mart.control_tower')
totals=dict(zip([x.name for x in q.description],q.fetchone()))
q=c.execute('SELECT control_tower_status,count(*) FROM mart.control_tower GROUP BY 1 ORDER BY 1');statuses=dict(q.fetchall())
q=c.execute("SELECT run_id,status,as_of_date,model_id,summary FROM ops.pipeline_run WHERE status='success' ORDER BY finished_at DESC LIMIT 1")
run=dict(zip([x.name for x in q.description],q.fetchone()))
result={'run':run,'totals':totals,'statuses':statuses,'cases':records}
destination=ROOT/'outputs/production/phase10'
destination.mkdir(parents=True,exist_ok=True)
(destination/'reconciliation.json').write_text(json.dumps(result,default=str,indent=2),encoding='utf-8')
print(json.dumps({'run':run,'totals':totals,'cases':{k:[v['outlook']['store_id'],v['outlook']['product_id'],v['math_checks']] for k,v in records.items()}},default=str,indent=2))
