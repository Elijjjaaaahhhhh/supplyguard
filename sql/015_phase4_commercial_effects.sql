\pset pager on

-- 1. ACTIVITY / PROMOTIONAL EFFECT

SELECT
    activity_flag,

    COUNT(*) AS observations,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        STDDEV_SAMP(sale_amount)::NUMERIC,
        4
    ) AS sales_std,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

GROUP BY activity_flag

ORDER BY activity_flag;


-- 2. HOLIDAY EFFECT

SELECT
    holiday_flag,

    COUNT(*) AS observations,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        STDDEV_SAMP(sale_amount)::NUMERIC,
        4
    ) AS sales_std,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

GROUP BY holiday_flag

ORDER BY holiday_flag;


-- 3. DISCOUNT DISTRIBUTION--

SELECT
    COUNT(*) AS observations,

    COUNT(DISTINCT discount) AS unique_discount_values,

    ROUND(
        MIN(discount)::NUMERIC,
        4
    ) AS minimum_discount,

    ROUND(
        MAX(discount)::NUMERIC,
        4
    ) AS maximum_discount,

    ROUND(
        AVG(discount)::NUMERIC,
        4
    ) AS average_discount,

    ROUND(
        PERCENTILE_CONT(0.25)
            WITHIN GROUP (ORDER BY discount)::NUMERIC,
        4
    ) AS p25,

    ROUND(
        PERCENTILE_CONT(0.50)
            WITHIN GROUP (ORDER BY discount)::NUMERIC,
        4
    ) AS median,

    ROUND(
        PERCENTILE_CONT(0.75)
            WITHIN GROUP (ORDER BY discount)::NUMERIC,
        4
    ) AS p75,

    ROUND(
        PERCENTILE_CONT(0.95)
            WITHIN GROUP (ORDER BY discount)::NUMERIC,
        4
    ) AS p95

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet';


-- 4. DISCOUNT VS NO-DISCOUNT BEHAVIOUR--
SELECT
    CASE
        WHEN discount = 1 THEN 'No discount'
        ELSE 'Discounted'
    END AS discount_status,

    COUNT(*) AS observations,

    ROUND(
        AVG(discount)::NUMERIC,
        4
    ) AS average_discount_value,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        STDDEV_SAMP(sale_amount)::NUMERIC,
        4
    ) AS sales_std,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

GROUP BY 1

ORDER BY MIN(discount);


-- 5. TOP 15 NETWORK SALES DAYS--


WITH daily_metrics AS (
    SELECT
        dt,

        SUM(sale_amount) AS total_sales,

        AVG(activity_flag) AS activity_rate,

        AVG(holiday_flag) AS holiday_rate,

        AVG(discount) AS average_discount,

        AVG(stockout_hours) AS average_stockout_hours

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY dt
)

SELECT
    dt,

    ROUND(
        total_sales::NUMERIC,
        2
    ) AS total_sales,

    ROUND(
        activity_rate::NUMERIC,
        4
    ) AS activity_rate,

    ROUND(
        holiday_rate::NUMERIC,
        4
    ) AS holiday_rate,

    ROUND(
        average_discount::NUMERIC,
        4
    ) AS average_discount,

    ROUND(
        average_stockout_hours::NUMERIC,
        4
    ) AS average_stockout_hours

FROM daily_metrics

ORDER BY total_sales DESC

LIMIT 15;


-- 6. DAILY ACTIVITY / HOLIDAY SUMMARY--

SELECT
    dt,

    ROUND(
        AVG(activity_flag)::NUMERIC,
        4
    ) AS activity_rate,

    ROUND(
        AVG(holiday_flag)::NUMERIC,
        4
    ) AS holiday_rate,

    ROUND(
        AVG(discount)::NUMERIC,
        4
    ) AS average_discount,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

AND (
        activity_flag = 1
        OR holiday_flag = 1
    )

GROUP BY dt

ORDER BY dt;


-- 7. COMBINED ACTIVITY + HOLIDAY EFFECT


SELECT
    activity_flag,
    holiday_flag,

    COUNT(*) AS observations,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours,

    ROUND(
        AVG(discount)::NUMERIC,
        4
    ) AS average_discount

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet'

GROUP BY
    activity_flag,
    holiday_flag

ORDER BY
    activity_flag,
    holiday_flag;