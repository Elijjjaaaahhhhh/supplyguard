

DROP VIEW IF EXISTS feature.v_demand_model_v2_eval;
DROP VIEW IF EXISTS feature.v_demand_model_v2_validation;
DROP VIEW IF EXISTS feature.v_demand_model_v2_dev_train;
DROP VIEW IF EXISTS feature.v_demand_model_v2;


CREATE VIEW feature.v_demand_model_v2 AS
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
    stockout_rolling_mean_7,

    -- Additional short-term lags
    LAG(
        target_sale_amount,
        2
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
    ) AS sales_lag_2,

    LAG(
        target_sale_amount,
        3
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
    ) AS sales_lag_3,

    -- Count how many historical observations
    -- actually exist in the 28-row window.
    COUNT(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
    ) AS history_count_28,

    -- 28-day historical demand level
    AVG(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_mean_28,

    -- Historical demand volatility
    STDDEV_SAMP(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_std_14,

    STDDEV_SAMP(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_std_28,

    -- Recent peak behaviour
    MAX(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_max_7,

    MAX(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_max_14,

    MAX(
        target_sale_amount
    ) OVER (
        PARTITION BY store_id, product_id
        ORDER BY dt
        ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
    ) AS sales_rolling_max_28,

    -- Difference between recent demand level
    -- and longer-term demand level.
    sales_rolling_mean_7
        -
        AVG(
            target_sale_amount
        ) OVER (
            PARTITION BY store_id, product_id
            ORDER BY dt
            ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
        )
        AS recent_growth_7_vs_28

FROM feature.daily_demand;