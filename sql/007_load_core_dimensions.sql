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
FROM staging.retail_daily
ON CONFLICT (product_id) DO NOTHING;


INSERT INTO core.dim_store (
    store_id,
    city_id,
    management_group_id
)
SELECT DISTINCT
    store_id,
    city_id,
    management_group_id
FROM staging.retail_daily
ON CONFLICT (store_id) DO NOTHING;


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
    TO_CHAR(dt, 'Day'),
    EXTRACT(WEEK FROM dt)::INTEGER,
    EXTRACT(ISODOW FROM dt) IN (6, 7)
FROM staging.retail_daily
ON CONFLICT (dt) DO NOTHING;