
-- Adds exogenous variables to the V2 historical feature set.



CREATE OR REPLACE VIEW feature.v_demand_model_v3 AS
SELECT
    v2.*,

    f.discount,
    f.activity_flag,

    f.precpt,
    f.avg_temperature,
    f.avg_humidity,
    f.avg_wind_level

FROM feature.v_demand_model_v2 AS v2

JOIN core.fact_daily_demand AS f
    ON v2.store_id = f.store_id
AND v2.product_id = f.product_id
AND v2.dt = f.dt;


CREATE OR REPLACE VIEW feature.v_demand_model_v3_dev_train AS
SELECT *
FROM feature.v_demand_model_v3
WHERE dt <= DATE '2024-06-11'
AND history_count_28 = 28;


CREATE OR REPLACE VIEW feature.v_demand_model_v3_validation AS
SELECT *
FROM feature.v_demand_model_v3
WHERE dt >= DATE '2024-06-12'
AND dt <= DATE '2024-06-25'
AND history_count_28 = 28;


CREATE OR REPLACE VIEW feature.v_demand_model_v3_eval AS
SELECT *
FROM feature.v_demand_model_v3
WHERE dt >= DATE '2024-06-26'
AND dt <= DATE '2024-07-02'
AND history_count_28 = 28;