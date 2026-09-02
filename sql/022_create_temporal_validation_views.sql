-- Development training:
--   2024-04-11 to 2024-06-11

-- Validation:
--   2024-06-12 to 2024-06-25

-- Final evaluation remains:
--   2024-06-26 to 2024-07-02


CREATE OR REPLACE VIEW feature.v_demand_model_dev_train AS
SELECT *
FROM feature.v_demand_model_train
WHERE dt <= DATE '2024-06-11';


CREATE OR REPLACE VIEW feature.v_demand_model_validation AS
SELECT *
FROM feature.v_demand_model_train
WHERE dt >= DATE '2024-06-12'
AND dt <= DATE '2024-06-25';