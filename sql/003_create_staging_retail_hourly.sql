CREATE TABLE IF NOT EXISTS staging.retail_hourly (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    dt DATE NOT NULL,
    hour_of_day SMALLINT NOT NULL,

    hourly_sale_amount DOUBLE PRECISION NOT NULL,
    out_of_stock_flag INTEGER NOT NULL,

    source_file TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT pk_staging_retail_hourly
        PRIMARY KEY (
            store_id,
            product_id,
            dt,
            hour_of_day
        ),

    CONSTRAINT chk_hour_of_day
        CHECK (hour_of_day BETWEEN 0 AND 23),

    CONSTRAINT chk_hourly_sale_nonnegative
        CHECK (hourly_sale_amount >= 0),

    CONSTRAINT chk_out_of_stock_flag
        CHECK (out_of_stock_flag IN (0, 1))
);