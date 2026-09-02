-- Model-Ready Feature Views
--
-- Purpose:
-- A leakage-safe training and evaluation datasets using
-- only features available before the target outcome occurs.
--
-- A 14-day warm-up is required because lag_14 is the longest
-- historical dependency in the baseline feature set.


CREATE OR REPLACE VIEW feature.v_demand_model_train AS
SELECT
    store_id,
    product_id,
    dt,

    target_sale_amount,

    first_category_id,
    second_category_id,
    third_category_id,

    day_of_week,
    is_weekend,
    holiday_flag,

    sales_lag_1,
    sales_lag_7,
    sales_lag_14,

    sales_rolling_mean_7,
    sales_rolling_mean_14,
    sales_rolling_std_7,

    stockout_lag_1,
    stockout_rolling_mean_7

FROM feature.daily_demand

WHERE source_file = 'train.parquet'

AND sales_lag_14 IS NOT NULL

AND sales_lag_1 IS NOT NULL
AND sales_lag_7 IS NOT NULL

AND sales_rolling_mean_7 IS NOT NULL
AND sales_rolling_mean_14 IS NOT NULL
AND sales_rolling_std_7 IS NOT NULL

AND stockout_lag_1 IS NOT NULL
AND stockout_rolling_mean_7 IS NOT NULL;


CREATE OR REPLACE VIEW feature.v_demand_model_eval AS
SELECT
    store_id,
    product_id,
    dt,

    target_sale_amount,

    first_category_id,
    second_category_id,
    third_category_id,

    day_of_week,
    is_weekend,
    holiday_flag,

    sales_lag_1,
    sales_lag_7,
    sales_lag_14,

    sales_rolling_mean_7,
    sales_rolling_mean_14,
    sales_rolling_std_7,

    stockout_lag_1,
    stockout_rolling_mean_7

FROM feature.daily_demand

WHERE source_file = 'eval.parquet'

AND sales_lag_14 IS NOT NULL

AND sales_lag_1 IS NOT NULL
AND sales_lag_7 IS NOT NULL

AND sales_rolling_mean_7 IS NOT NULL
AND sales_rolling_mean_14 IS NOT NULL
AND sales_rolling_std_7 IS NOT NULL

AND stockout_lag_1 IS NOT NULL
AND stockout_rolling_mean_7 IS NOT NULL;