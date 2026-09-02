WITH base AS (
    SELECT
        f.store_id,
        f.product_id,
        f.dt,

        f.sale_amount AS target_sale_amount,

        p.first_category_id,
        p.second_category_id,
        p.third_category_id,

        d.day_of_week::SMALLINT AS day_of_week,
        d.is_weekend,

        f.holiday_flag::SMALLINT AS holiday_flag,

        f.stockout_hours,

        f.source_file,

        LAG(
            f.sale_amount,
            1
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
        ) AS sales_lag_1,

        LAG(
            f.sale_amount,
            7
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
        ) AS sales_lag_7,

        LAG(
            f.sale_amount,
            14
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
        ) AS sales_lag_14,

        AVG(
            f.sale_amount
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
            ROWS BETWEEN
                7 PRECEDING
                AND 1 PRECEDING
        ) AS sales_rolling_mean_7,

        AVG(
            f.sale_amount
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
            ROWS BETWEEN
                14 PRECEDING
                AND 1 PRECEDING
        ) AS sales_rolling_mean_14,

        STDDEV_SAMP(
            f.sale_amount
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
            ROWS BETWEEN
                7 PRECEDING
                AND 1 PRECEDING
        ) AS sales_rolling_std_7,

        LAG(
            f.stockout_hours,
            1
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
        )::SMALLINT AS stockout_lag_1,

        AVG(
            f.stockout_hours
        ) OVER (
            PARTITION BY
                f.store_id,
                f.product_id
            ORDER BY
                f.dt
            ROWS BETWEEN
                7 PRECEDING
                AND 1 PRECEDING
        ) AS stockout_rolling_mean_7

    FROM core.fact_daily_demand AS f

    JOIN core.dim_product AS p
        ON f.product_id = p.product_id

    JOIN core.dim_date AS d
        ON f.dt = d.dt
)

INSERT INTO feature.daily_demand (
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

    source_file
)

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

    source_file

FROM base

ON CONFLICT (
    store_id,
    product_id,
    dt
)
DO NOTHING;