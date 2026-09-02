\pset pager off

SELECT
    DATE_TRUNC('week', dt)::DATE AS week_start,
    SUM(sale_amount) AS total_sales,
    AVG(sale_amount) AS average_sales,
    AVG(stockout_hours) AS average_stockout_hours
FROM core.fact_daily_demand
WHERE source_file = 'train.parquet'
GROUP BY DATE_TRUNC('week', dt)::DATE
ORDER BY week_start;



SELECT
    d.day_of_week,
    TRIM(d.day_name) AS day_name,

    AVG(f.sale_amount) AS average_sales,

    STDDEV_SAMP(f.sale_amount) AS sales_std,

    AVG(f.stockout_hours) AS average_stockout_hours

FROM core.fact_daily_demand AS f

JOIN core.dim_date AS d
    ON f.dt = d.dt

WHERE f.source_file = 'train.parquet'

GROUP BY
    d.day_of_week,
    TRIM(d.day_name)

ORDER BY d.day_of_week;


WITH weekly_segments AS (
    SELECT
        DATE_TRUNC('week', f.dt)::DATE AS week_start,

        d.is_weekend,

        AVG(f.sale_amount) AS average_sales

    FROM core.fact_daily_demand AS f

    JOIN core.dim_date AS d
        ON f.dt = d.dt

    WHERE f.source_file = 'train.parquet'

    GROUP BY
        DATE_TRUNC('week', f.dt)::DATE,
        d.is_weekend
)

SELECT
    week_start,

    MAX(average_sales) FILTER (
        WHERE is_weekend = FALSE
    ) AS weekday_average,

    MAX(average_sales) FILTER (
        WHERE is_weekend = TRUE
    ) AS weekend_average,

    MAX(average_sales) FILTER (
        WHERE is_weekend = TRUE
    )
    -
    MAX(average_sales) FILTER (
        WHERE is_weekend = FALSE
    ) AS weekend_uplift

FROM weekly_segments

GROUP BY week_start

ORDER BY week_start;



WITH dated AS (
    SELECT
        dt,
        sale_amount,

        CASE
            WHEN dt <= DATE '2024-04-26'
                THEN 'First 30 days'

            WHEN dt >= DATE '2024-05-27'
                THEN 'Last 30 days'

            ELSE 'Middle period'
        END AS period

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'
)

SELECT
    period,
    COUNT(*) AS observations,
    AVG(sale_amount) AS average_sales,
    SUM(sale_amount) AS total_sales

FROM dated

GROUP BY period

ORDER BY
    CASE period
        WHEN 'First 30 days' THEN 1
        WHEN 'Middle period' THEN 2
        ELSE 3
    END;



