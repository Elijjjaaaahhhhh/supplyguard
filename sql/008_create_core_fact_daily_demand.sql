CREATE TABLE IF NOT EXISTS core.fact_daily_demand (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    dt DATE NOT NULL,

    sale_amount DOUBLE PRECISION NOT NULL,
    stockout_hours SMALLINT NOT NULL,

    discount DOUBLE PRECISION NOT NULL,
    holiday_flag SMALLINT NOT NULL,
    activity_flag SMALLINT NOT NULL,

    precpt DOUBLE PRECISION NOT NULL,
    avg_temperature DOUBLE PRECISION NOT NULL,
    avg_humidity DOUBLE PRECISION NOT NULL,
    avg_wind_level DOUBLE PRECISION NOT NULL,

    source_file TEXT NOT NULL,

    CONSTRAINT pk_fact_daily_demand
        PRIMARY KEY (
            store_id,
            product_id,
            dt
        ),

    CONSTRAINT fk_fact_store
        FOREIGN KEY (store_id)
        REFERENCES core.dim_store(store_id),

    CONSTRAINT fk_fact_product
        FOREIGN KEY (product_id)
        REFERENCES core.dim_product(product_id),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (dt)
        REFERENCES core.dim_date(dt),

    CONSTRAINT chk_fact_sale_nonnegative
        CHECK (sale_amount >= 0),

    CONSTRAINT chk_fact_stockout_hours
        CHECK (stockout_hours BETWEEN 0 AND 16),

    CONSTRAINT chk_fact_holiday
        CHECK (holiday_flag IN (0, 1)),

    CONSTRAINT chk_fact_activity
        CHECK (activity_flag IN (0, 1))
);