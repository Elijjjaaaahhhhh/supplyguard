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
FROM staging.retail_daily
ON CONFLICT (
    store_id,
    product_id,
    dt
)
DO NOTHING;