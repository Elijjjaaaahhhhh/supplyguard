\pset pager off

SELECT
    COUNT(*) AS observations,
    COUNT(DISTINCT product_id) AS products,
    COUNT(DISTINCT store_id) AS stores,
    COUNT(DISTINCT dt) AS dates,
    SUM(sale_amount) AS total_sales,
    AVG(sale_amount) AS average_daily_sales,
    AVG(stockout_hours) AS average_stockout_hours
FROM core.fact_daily_demand
WHERE source_file = 'train.parquet';




SELECT
    dt,
    SUM(sale_amount) AS total_sales,
    AVG(sale_amount) AS average_sales_per_series,
    AVG(stockout_hours) AS average_stockout_hours
FROM core.fact_daily_demand
WHERE source_file = 'train.parquet'
GROUP BY dt
ORDER BY dt;




SELECT
    d.is_weekend,
    COUNT(*) AS observations,
    AVG(f.sale_amount) AS average_sales,
    AVG(f.stockout_hours) AS average_stockout_hours,
    SUM(f.sale_amount) AS total_sales
FROM core.fact_daily_demand AS f
JOIN core.dim_date AS d
    ON f.dt = d.dt
WHERE f.source_file = 'train.parquet'
GROUP BY d.is_weekend
ORDER BY d.is_weekend;




WITH product_sales AS (
    SELECT
        product_id,
        SUM(sale_amount) AS total_sales
    FROM core.fact_daily_demand
    WHERE source_file = 'train.parquet'
    GROUP BY product_id
)
SELECT
    product_id,
    total_sales,
    total_sales
        / SUM(total_sales) OVER () * 100
        AS percentage_of_total_sales
FROM product_sales
ORDER BY total_sales DESC
LIMIT 20;




WITH store_sales AS (
    SELECT
        store_id,
        SUM(sale_amount) AS total_sales
    FROM core.fact_daily_demand
    WHERE source_file = 'train.parquet'
    GROUP BY store_id
)
SELECT
    store_id,
    total_sales,
    total_sales
        / SUM(total_sales) OVER () * 100
        AS percentage_of_total_sales
FROM store_sales
ORDER BY total_sales DESC
LIMIT 20;




SELECT
    COUNT(*) AS observations,

    COUNT(*) FILTER (
        WHERE stockout_hours > 0
    ) AS observations_with_stockout,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE stockout_hours > 0
        )
        / COUNT(*),
        2
    ) AS stockout_observation_rate,

    AVG(stockout_hours) AS average_stockout_hours

FROM core.fact_daily_demand
WHERE source_file = 'train.parquet';




SELECT
    CASE
        WHEN stockout_hours = 0 THEN 'No stockout'
        WHEN stockout_hours BETWEEN 1 AND 4 THEN '1-4 hours'
        WHEN stockout_hours BETWEEN 5 AND 8 THEN '5-8 hours'
        WHEN stockout_hours BETWEEN 9 AND 12 THEN '9-12 hours'
        WHEN stockout_hours BETWEEN 13 AND 16 THEN '13-16 hours'
    END AS stockout_band,

    COUNT(*) AS observations,
    AVG(sale_amount) AS average_sales,

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
GROUP BY
    CASE
        WHEN stockout_hours = 0 THEN 'No stockout'
        WHEN stockout_hours BETWEEN 1 AND 4 THEN '1-4 hours'
        WHEN stockout_hours BETWEEN 5 AND 8 THEN '5-8 hours'
        WHEN stockout_hours BETWEEN 9 AND 12 THEN '9-12 hours'
        WHEN stockout_hours BETWEEN 13 AND 16 THEN '13-16 hours'
    END
ORDER BY
    MIN(stockout_hours);


