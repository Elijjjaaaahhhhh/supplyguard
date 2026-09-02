CREATE TABLE IF NOT EXISTS mart.inventory_decision (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    -- Demand inputs
    expected_daily_demand DOUBLE PRECISION NOT NULL,
    demand_std DOUBLE PRECISION NOT NULL,

    -- Inventory inputs
    on_hand_quantity DOUBLE PRECISION NOT NULL,
    on_order_quantity DOUBLE PRECISION NOT NULL,
    backorder_quantity DOUBLE PRECISION NOT NULL,
    inventory_position DOUBLE PRECISION NOT NULL,

    -- Supplier / policy inputs
    supplier_id BIGINT NOT NULL,
    average_lead_time_days DOUBLE PRECISION NOT NULL,
    lead_time_std_days DOUBLE PRECISION NOT NULL,
    target_service_level DOUBLE PRECISION NOT NULL,
    planning_horizon_days INTEGER NOT NULL,

    -- Decision calculations
    lead_time_demand DOUBLE PRECISION NOT NULL,
    safety_stock DOUBLE PRECISION NOT NULL,
    reorder_point DOUBLE PRECISION NOT NULL,

    days_of_supply DOUBLE PRECISION,
    coverage_gap_days DOUBLE PRECISION,

    reorder_required BOOLEAN NOT NULL,

    target_stock_level DOUBLE PRECISION NOT NULL,
    raw_order_quantity DOUBLE PRECISION NOT NULL,

    -- Commercial constraints used later
    minimum_order_quantity DOUBLE PRECISION NOT NULL,
    case_pack_size DOUBLE PRECISION NOT NULL,
    unit_cost DOUBLE PRECISION,
    working_capital_limit DOUBLE PRECISION,
    warehouse_capacity_remaining DOUBLE PRECISION,

    -- Priority / economics
    stockout_cost_per_unit DOUBLE PRECISION,
    holding_cost_per_unit_day DOUBLE PRECISION,
    shelf_life_days INTEGER,
    priority_weight DOUBLE PRECISION NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_inventory_decision
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);