\pset pager on


-- 1. Product-level demand profile

WITH product_metrics AS (
    SELECT
        product_id,

        COUNT(*) AS observations,

        COUNT(DISTINCT store_id) AS stores,

        AVG(sale_amount) AS mean_sales,

        STDDEV_SAMP(sale_amount) AS sales_std,

        MAX(sale_amount) AS max_sales,

        COUNT(*) FILTER (
            WHERE sale_amount = 0
        )::DOUBLE PRECISION
        / COUNT(*) AS zero_sales_fraction

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY product_id
)

SELECT
    product_id,
    observations,
    stores,

    ROUND(mean_sales::NUMERIC, 4)
        AS mean_sales,

    ROUND(sales_std::NUMERIC, 4)
        AS sales_std,

    ROUND(
        (sales_std / NULLIF(mean_sales, 0))::NUMERIC,
        4
    ) AS coefficient_of_variation,

    ROUND(max_sales::NUMERIC, 4)
        AS max_sales,

    ROUND(
        zero_sales_fraction::NUMERIC,
        4
    ) AS zero_sales_fraction

FROM product_metrics

ORDER BY
    sales_std / NULLIF(mean_sales, 0) DESC NULLS LAST

LIMIT 25;


-- 2. Focus on product 536


SELECT
    product_id,

    COUNT(DISTINCT store_id)
        AS stores,

    COUNT(*)
        AS observations,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        STDDEV_SAMP(sale_amount)::NUMERIC,
        4
    ) AS sales_std,

    ROUND(
        (
            STDDEV_SAMP(sale_amount)
            / NULLIF(AVG(sale_amount), 0)
        )::NUMERIC,
        4
    ) AS coefficient_of_variation,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours,

    ROUND(
        (
            COUNT(*) FILTER (
                WHERE sale_amount = 0
            )::DOUBLE PRECISION
            / COUNT(*)
        )::NUMERIC,
        4
    ) AS zero_sales_fraction

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'
AND product_id = 536

GROUP BY product_id;


-- 3. Product 536 by store


SELECT
    store_id,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        STDDEV_SAMP(sale_amount)::NUMERIC,
        4
    ) AS sales_std,

    ROUND(
        (
            STDDEV_SAMP(sale_amount)
            / NULLIF(AVG(sale_amount), 0)
        )::NUMERIC,
        4
    ) AS coefficient_of_variation,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'
AND product_id = 536

GROUP BY store_id

ORDER BY
    STDDEV_SAMP(sale_amount)
    / NULLIF(AVG(sale_amount), 0)
    DESC NULLS LAST

LIMIT 25;


-- 4. Compare product 536 against network product behaviour


WITH product_metrics AS (
    SELECT
        product_id,

        AVG(sale_amount) AS mean_sales,

        STDDEV_SAMP(sale_amount) AS sales_std

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY product_id
)

SELECT
    COUNT(*) AS products,

    ROUND(
        AVG(
            sales_std / NULLIF(mean_sales, 0)
        )::NUMERIC,
        4
    ) AS average_product_cv,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY
                sales_std / NULLIF(mean_sales, 0)
        )::NUMERIC,
        4
    ) AS median_product_cv,

    ROUND(
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (
            ORDER BY
                sales_std / NULLIF(mean_sales, 0)
        )::NUMERIC,
        4
    ) AS p95_product_cv

FROM product_metrics;