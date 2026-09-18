CREATE TABLE IF NOT EXISTS ops.forecast_evaluation (
 store_id BIGINT NOT NULL, product_id BIGINT NOT NULL, dt DATE NOT NULL,
 actual DOUBLE PRECISION NOT NULL CHECK(actual>=0 AND actual<'Infinity'::float8),
 prediction DOUBLE PRECISION NOT NULL CHECK(prediction>=0 AND prediction<'Infinity'::float8),
 rolling_prediction DOUBLE PRECISION NOT NULL CHECK(rolling_prediction>=0 AND rolling_prediction<'Infinity'::float8),
 source_sha256 TEXT NOT NULL, model_version TEXT NOT NULL DEFAULT 'V3C historical holdout',
 PRIMARY KEY(store_id,product_id,dt)
);
CREATE OR REPLACE VIEW mart.bi_demand_history AS
 SELECT f.store_id,f.product_id,f.dt,f.sale_amount,f.stockout_hours
 FROM core.fact_daily_demand f JOIN mart.control_tower c USING(store_id,product_id)
 WHERE f.dt<=c.decision_date;
CREATE OR REPLACE VIEW mart.bi_forecast_evaluation AS
 SELECT store_id,product_id,dt,actual,prediction,rolling_prediction,model_version,source_sha256
 FROM ops.forecast_evaluation;
CREATE OR REPLACE VIEW mart.bi_forecast_outlook AS
 SELECT c.store_id,c.product_id,f.as_of_date,f.target_date AS forecast_date,
 f.prediction AS predicted_demand,f.model_id,f.run_id::text AS forecast_run_id,
 r.finished_at AS generated_at,f.input_policy,
 c.on_hand_quantity,c.on_order_quantity,c.backorder_quantity,c.inventory_position,
 c.days_of_supply,c.average_lead_time_days,c.coverage_gap_days,c.safety_stock,c.reorder_point,
 c.raw_order_quantity,c.final_recommended_quantity,c.allocated_quantity,c.allocated_order_value,
 c.capital_constrained,c.capacity_constrained,c.shelf_life_constrained,
 c.urgency_score,c.urgency_band,c.control_tower_status,c.recommended_action,c.funding_status,
 o.minimum_order_quantity,o.case_pack_size,
 (r.config->>'budget')::float8 AS scenario_budget
 FROM mart.control_tower c JOIN ops.forecast f
 ON f.run_id=c.forecast_run_id AND f.store_id=c.store_id AND f.product_id=c.product_id
 AND f.target_date=c.forecast_target_date
 JOIN ops.pipeline_run r ON r.run_id=f.run_id
 JOIN mart.order_recommendation o ON o.store_id=c.store_id AND o.product_id=c.product_id AND o.decision_date=c.decision_date;
COMMENT ON VIEW mart.bi_demand_history IS 'Observed sales for published scenario series; sales are stockout-censored.';
COMMENT ON VIEW mart.bi_forecast_evaluation IS 'Historical one-day held-out predictions, not operational future forecasts.';
COMMENT ON VIEW mart.bi_forecast_outlook IS 'Persisted next-day prediction with synthetic inventory and procurement inputs; horizon demand is constant-level extrapolation.';
