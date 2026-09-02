CREATE TABLE IF NOT EXISTS feature.daily_demand (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    dt DATE NOT NULL,

    -- Target
    target_sale_amount DOUBLE PRECISION NOT NULL,

    -- Product context
    first_category_id BIGINT NOT NULL,
    second_category_id BIGINT NOT NULL,
    third_category_id BIGINT NOT NULL,

    -- Calendar features
    day_of_week SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    holiday_flag SMALLINT NOT NULL,

    -- Demand lag features
    sales_lag_1 DOUBLE PRECISION,
    sales_lag_7 DOUBLE PRECISION,
    sales_lag_14 DOUBLE PRECISION,

    -- Demand rolling features
    sales_rolling_mean_7 DOUBLE PRECISION,
    sales_rolling_mean_14 DOUBLE PRECISION,
    sales_rolling_std_7 DOUBLE PRECISION,

    -- Availability-history features
    stockout_lag_1 SMALLINT,
    stockout_rolling_mean_7 DOUBLE PRECISION,

    source_file TEXT NOT NULL,

    CONSTRAINT pk_feature_daily_demand
        PRIMARY KEY (
            store_id,
            product_id,
            dt
        )
);