CREATE OR REPLACE VIEW staging.v_retail_hourly AS
SELECT
    r.store_id,
    r.product_id,
    r.dt::DATE AS dt,

    h.hour_index - 1 AS hour_of_day,

    r.hours_sale[h.hour_index] AS hourly_sale_amount,
    r.hours_stock_status[h.hour_index] AS out_of_stock_flag,

    r.source_file,
    r.ingested_at

FROM raw.retail_daily AS r

CROSS JOIN LATERAL
    generate_series(1, 24) AS h(hour_index);