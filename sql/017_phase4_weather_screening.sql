
-- 1. Overall weather ranges

SELECT
    ROUND(MIN(precpt)::NUMERIC, 2) AS min_precipitation,
    ROUND(MAX(precpt)::NUMERIC, 2) AS max_precipitation,
    ROUND(AVG(precpt)::NUMERIC, 2) AS avg_precipitation,

    ROUND(MIN(avg_temperature)::NUMERIC, 2) AS min_temperature,
    ROUND(MAX(avg_temperature)::NUMERIC, 2) AS max_temperature,
    ROUND(AVG(avg_temperature)::NUMERIC, 2) AS avg_temperature,

    ROUND(MIN(avg_humidity)::NUMERIC, 2) AS min_humidity,
    ROUND(MAX(avg_humidity)::NUMERIC, 2) AS max_humidity,
    ROUND(AVG(avg_humidity)::NUMERIC, 2) AS avg_humidity,

    ROUND(MIN(avg_wind_level)::NUMERIC, 2) AS min_wind,
    ROUND(MAX(avg_wind_level)::NUMERIC, 2) AS max_wind,
    ROUND(AVG(avg_wind_level)::NUMERIC, 2) AS avg_wind

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet';


-- 2. Simple linear correlations with observed sales


SELECT
    ROUND(
        CORR(sale_amount, precpt)::NUMERIC,
        4
    ) AS sales_precipitation_corr,

    ROUND(
        CORR(sale_amount, avg_temperature)::NUMERIC,
        4
    ) AS sales_temperature_corr,

    ROUND(
        CORR(sale_amount, avg_humidity)::NUMERIC,
        4
    ) AS sales_humidity_corr,

    ROUND(
        CORR(sale_amount, avg_wind_level)::NUMERIC,
        4
    ) AS sales_wind_corr

FROM core.fact_daily_demand

WHERE source_file = 'train.parquet';


-- 3. Precipitation bands


WITH weather_bands AS (
    SELECT
        sale_amount,
        stockout_hours,

        CASE
            WHEN precpt = 0
                THEN 'No precipitation'

            WHEN precpt <= 2
                THEN 'Low'

            WHEN precpt <= 10
                THEN 'Moderate'

            ELSE 'High'
        END AS precipitation_band,

        CASE
            WHEN precpt = 0 THEN 1
            WHEN precpt <= 2 THEN 2
            WHEN precpt <= 10 THEN 3
            ELSE 4
        END AS band_order

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'
)

SELECT
    precipitation_band,

    COUNT(*) AS observations,

    ROUND(
        AVG(sale_amount)::NUMERIC,
        4
    ) AS average_sales,

    ROUND(
        AVG(stockout_hours)::NUMERIC,
        4
    ) AS average_stockout_hours

FROM weather_bands

GROUP BY
    precipitation_band,
    band_order

ORDER BY band_order;


-- 4. Weather correlation at network-day level


WITH daily_weather AS (
    SELECT
        dt,

        AVG(sale_amount) AS average_sales,

        AVG(precpt) AS precipitation,

        AVG(avg_temperature) AS temperature,

        AVG(avg_humidity) AS humidity,

        AVG(avg_wind_level) AS wind

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY dt
)

SELECT
    ROUND(
        CORR(average_sales, precipitation)::NUMERIC,
        4
    ) AS daily_sales_precipitation_corr,

    ROUND(
        CORR(average_sales, temperature)::NUMERIC,
        4
    ) AS daily_sales_temperature_corr,

    ROUND(
        CORR(average_sales, humidity)::NUMERIC,
        4
    ) AS daily_sales_humidity_corr,

    ROUND(
        CORR(average_sales, wind)::NUMERIC,
        4
    ) AS daily_sales_wind_corr

FROM daily_weather;