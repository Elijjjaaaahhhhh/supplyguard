
-- Model V2 temporal splits


CREATE OR REPLACE VIEW feature.v_demand_model_v2_dev_train AS
SELECT *
FROM feature.v_demand_model_v2
WHERE dt <= DATE '2024-06-11'
AND history_count_28 = 28;


CREATE OR REPLACE VIEW feature.v_demand_model_v2_validation AS
SELECT *
FROM feature.v_demand_model_v2
WHERE dt >= DATE '2024-06-12'
AND dt <= DATE '2024-06-25'
AND history_count_28 = 28;


CREATE OR REPLACE VIEW feature.v_demand_model_v2_eval AS
SELECT *
FROM feature.v_demand_model_v2
WHERE dt >= DATE '2024-06-26'
AND dt <= DATE '2024-07-02'
AND history_count_28 = 28;