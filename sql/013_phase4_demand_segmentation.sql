\pset pager off

WITH series_metrics AS (
    SELECT
        store_id,
        product_id,

        COUNT(*) AS days_observed,

        AVG(sale_amount) AS mean_daily_sales,

        STDDEV_SAMP(sale_amount) AS std_daily_sales,

        COUNT(*) FILTER (
            WHERE sale_amount = 0
        ) AS zero_sales_days,

        MAX(sale_amount) AS max_daily_sales

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY
        store_id,
        product_id
)

SELECT
    COUNT(*) AS series_count,

    AVG(mean_daily_sales) AS avg_series_mean_sales,

    AVG(std_daily_sales) AS avg_series_std_sales,

    AVG(
        zero_sales_days::DOUBLE PRECISION
        / days_observed
    ) AS avg_zero_sales_fraction,

    AVG(max_daily_sales) AS avg_series_max_sales

FROM series_metrics;




WITH series_metrics AS (
    SELECT
        store_id,
        product_id,

        AVG(sale_amount) AS mean_daily_sales,

        STDDEV_SAMP(sale_amount) AS std_daily_sales

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY
        store_id,
        product_id
)

SELECT
    store_id,
    product_id,
    mean_daily_sales,
    std_daily_sales,

    CASE
        WHEN mean_daily_sales > 0
        THEN std_daily_sales / mean_daily_sales
    END AS coefficient_of_variation

FROM series_metrics

ORDER BY coefficient_of_variation DESC NULLS LAST

LIMIT 20;



WITH series_metrics AS (
    SELECT
        store_id,
        product_id,

        COUNT(*) AS days_observed,

        COUNT(*) FILTER (
            WHERE sale_amount = 0
        ) AS zero_sales_days,

        AVG(sale_amount) AS mean_daily_sales

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY
        store_id,
        product_id
),

banded_series AS (
    SELECT
        store_id,
        product_id,
        mean_daily_sales,

        zero_sales_days::DOUBLE PRECISION
            / days_observed AS zero_sales_fraction,

        CASE
            WHEN zero_sales_days = 0
                THEN '0%'

            WHEN zero_sales_days::DOUBLE PRECISION
                 / days_observed <= 0.10
                THEN '0-10%'

            WHEN zero_sales_days::DOUBLE PRECISION
                 / days_observed <= 0.25
                THEN '10-25%'

            WHEN zero_sales_days::DOUBLE PRECISION
                 / days_observed <= 0.50
                THEN '25-50%'

            ELSE '>50%'
        END AS zero_sales_band

    FROM series_metrics
)

SELECT
    zero_sales_band,

    COUNT(*) AS series_count,

    AVG(mean_daily_sales) AS average_mean_sales,

    AVG(zero_sales_fraction) AS average_zero_sales_fraction

FROM banded_series

GROUP BY zero_sales_band

ORDER BY
    CASE
        WHEN zero_sales_band = '0%' THEN 1
        WHEN zero_sales_band = '0-10%' THEN 2
        WHEN zero_sales_band = '10-25%' THEN 3
        WHEN zero_sales_band = '25-50%' THEN 4
        ELSE 5
    END;



SELECT
    CASE
        WHEN stockout_hours = 0
            THEN 'No stockout'
        WHEN stockout_hours BETWEEN 1 AND 8
            THEN '1-8 hours'
        ELSE '9-16 hours'
    END AS stockout_condition,

    COUNT(*) FILTER (
        WHERE sale_amount = 0
    ) AS zero_sales_rows,

    COUNT(*) AS observations,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sale_amount = 0
        )
        / COUNT(*),
        2
    ) AS zero_sales_rate

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

GROUP BY 1

ORDER BY
    MIN(stockout_hours);




