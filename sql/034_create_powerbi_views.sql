-- Creates stable BI-facing views so Power BI does not depend
-- directly on implementation-layer tables.

-- CONTROL TOWER FACT

CREATE OR REPLACE VIEW mart.bi_control_tower AS

SELECT
    store_id,
    product_id,
    decision_date,

    expected_daily_demand,
    demand_std,

    on_hand_quantity,
    on_order_quantity,
    backorder_quantity,
    inventory_position,

    days_of_supply,
    average_lead_time_days,
    coverage_gap_days,

    safety_stock,
    reorder_point,
    reorder_required,

    raw_order_quantity,
    final_recommended_quantity,

    capital_constrained,
    capacity_constrained,
    shelf_life_constrained,

    urgency_score,
    urgency_band,

    stockout_cost_per_unit,
    on_time_delivery_rate,
    priority_weight,

    allocated_quantity,
    allocated_order_value,
    funding_status,

    control_tower_status,
    recommended_action

FROM mart.control_tower;


-- ============================================================
-- PRODUCT DIMENSION
-- ============================================================

CREATE OR REPLACE VIEW mart.bi_dim_product AS

SELECT
    product_id,

    first_category_id,
    second_category_id,
    third_category_id

FROM core.dim_product;


-- ============================================================
-- STORE DIMENSION
-- ============================================================

CREATE OR REPLACE VIEW mart.bi_dim_store AS

SELECT
    store_id,
    city_id,
    management_group_id

FROM core.dim_store;


-- ============================================================
-- DATE DIMENSION
-- ============================================================

CREATE OR REPLACE VIEW mart.bi_dim_date AS

SELECT
    dt,
    year,
    month,
    day,
    day_of_week,
    day_name,
    week_of_year,
    is_weekend

FROM core.dim_date;