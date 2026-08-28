CREATE TABLE IF NOT EXISTS staging.retail_daily (
    city_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    management_group_id BIGINT NOT NULL,
    first_category_id BIGINT NOT NULL,
    second_category_id BIGINT NOT NULL,
    third_category_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,

    dt DATE NOT NULL,

    sale_amount DOUBLE PRECISION NOT NULL,
    stock_hour6_22_cnt INTEGER NOT NULL,

    discount DOUBLE PRECISION NOT NULL,
    holiday_flag INTEGER NOT NULL,
    activity_flag INTEGER NOT NULL,

    precpt DOUBLE PRECISION NOT NULL,
    avg_temperature DOUBLE PRECISION NOT NULL,
    avg_humidity DOUBLE PRECISION NOT NULL,
    avg_wind_level DOUBLE PRECISION NOT NULL,

    source_file TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT pk_staging_retail_daily
        PRIMARY KEY (store_id, product_id, dt),

    CONSTRAINT chk_stock_hour6_22_cnt
        CHECK (stock_hour6_22_cnt BETWEEN 0 AND 16),

    CONSTRAINT chk_sale_amount_nonnegative
        CHECK (sale_amount >= 0),

    CONSTRAINT chk_holiday_flag
        CHECK (holiday_flag IN (0, 1)),

    CONSTRAINT chk_activity_flag
        CHECK (activity_flag IN (0, 1))
);