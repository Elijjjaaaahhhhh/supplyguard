BEGIN;

TRUNCATE TABLE
    core.fact_daily_demand,
    core.dim_product,
    core.dim_store,
    core.dim_date,
    staging.retail_daily
CASCADE;

INSERT INTO staging.retail_daily (
    city_id,
    store_id,
    management_group_id,
    first_category_id,
    second_category_id,
    third_category_id,
    product_id,
    dt,
    sale_amount,
    stock_hour6_22_cnt,
    discount,
    holiday_flag,
    activity_flag,
    precpt,
    avg_temperature,
    avg_humidity,
    avg_wind_level,
    source_file,
    ingested_at
)
SELECT
    city_id,
    store_id,
    management_group_id,
    first_category_id,
    second_category_id,
    third_category_id,
    product_id,
    dt::DATE,
    sale_amount,
    stock_hour6_22_cnt,
    discount,
    holiday_flag,
    activity_flag,
    precpt,
    avg_temperature,
    avg_humidity,
    avg_wind_level,
    source_file,
    ingested_at
FROM raw.retail_daily;


INSERT INTO core.dim_product (
    product_id,
    first_category_id,
    second_category_id,
    third_category_id
)
SELECT DISTINCT
    product_id,
    first_category_id,
    second_category_id,
    third_category_id
FROM staging.retail_daily;


INSERT INTO core.dim_store (
    store_id,
    city_id,
    management_group_id
)
SELECT DISTINCT
    store_id,
    city_id,
    management_group_id
FROM staging.retail_daily;


INSERT INTO core.dim_date (
    dt,
    year,
    month,
    day,
    day_of_week,
    day_name,
    week_of_year,
    is_weekend
)
SELECT DISTINCT
    dt,
    EXTRACT(YEAR FROM dt)::INTEGER,
    EXTRACT(MONTH FROM dt)::INTEGER,
    EXTRACT(DAY FROM dt)::INTEGER,
    EXTRACT(ISODOW FROM dt)::INTEGER,
    TRIM(TO_CHAR(dt, 'Day')),
    EXTRACT(WEEK FROM dt)::INTEGER,
    EXTRACT(ISODOW FROM dt) IN (6, 7)
FROM staging.retail_daily;


INSERT INTO core.fact_daily_demand (
    store_id,
    product_id,
    dt,
    sale_amount,
    stockout_hours,
    discount,
    holiday_flag,
    activity_flag,
    precpt,
    avg_temperature,
    avg_humidity,
    avg_wind_level,
    source_file
)
SELECT
    store_id,
    product_id,
    dt,
    sale_amount,
    stock_hour6_22_cnt::SMALLINT,
    discount,
    holiday_flag::SMALLINT,
    activity_flag::SMALLINT,
    precpt,
    avg_temperature,
    avg_humidity,
    avg_wind_level,
    source_file
FROM staging.retail_daily;

COMMIT;