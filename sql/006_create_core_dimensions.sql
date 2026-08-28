CREATE TABLE IF NOT EXISTS core.dim_product (
    product_id BIGINT PRIMARY KEY,
    first_category_id BIGINT NOT NULL,
    second_category_id BIGINT NOT NULL,
    third_category_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.dim_store (
    store_id BIGINT PRIMARY KEY,
    city_id BIGINT NOT NULL,
    management_group_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.dim_date (
    dt DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    week_of_year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
);