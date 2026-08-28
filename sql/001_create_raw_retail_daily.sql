CREATE TABLE IF NOT EXISTS raw.retail_daily (
    city_id BIGINT,
    store_id BIGINT,
    management_group_id BIGINT,
    first_category_id BIGINT,
    second_category_id BIGINT,
    third_category_id BIGINT,
    product_id BIGINT,
    dt TEXT,
    sale_amount DOUBLE PRECISION,
    hours_sale DOUBLE PRECISION[],
    stock_hour6_22_cnt INTEGER,
    hours_stock_status INTEGER[],
    discount DOUBLE PRECISION,
    holiday_flag INTEGER,
    activity_flag INTEGER,
    precpt DOUBLE PRECISION,
    avg_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    avg_wind_level DOUBLE PRECISION,

    source_file TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);