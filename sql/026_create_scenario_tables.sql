

CREATE SCHEMA IF NOT EXISTS scenario;

ALTER SCHEMA scenario OWNER TO supplyguard_app;


-- 1. INVENTORY POSITION

CREATE TABLE IF NOT EXISTS scenario.inventory_position (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,

    as_of_date DATE NOT NULL,

    on_hand_quantity DOUBLE PRECISION NOT NULL,

    on_order_quantity DOUBLE PRECISION NOT NULL
        DEFAULT 0,

    backorder_quantity DOUBLE PRECISION NOT NULL
        DEFAULT 0,

    expected_next_receipt_date DATE,

    unit_cost DOUBLE PRECISION,

    warehouse_capacity_remaining DOUBLE PRECISION,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_scenario_inventory_position
        PRIMARY KEY (
            store_id,
            product_id,
            as_of_date
        ),

    CONSTRAINT ck_inventory_on_hand_nonnegative
        CHECK (
            on_hand_quantity >= 0
        ),

    CONSTRAINT ck_inventory_on_order_nonnegative
        CHECK (
            on_order_quantity >= 0
        ),

    CONSTRAINT ck_inventory_backorder_nonnegative
        CHECK (
            backorder_quantity >= 0
        )
);


-- 2. SUPPLIER POLICY

CREATE TABLE IF NOT EXISTS scenario.supplier_policy (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,

    supplier_id BIGINT NOT NULL,

    average_lead_time_days DOUBLE PRECISION NOT NULL,

    lead_time_std_days DOUBLE PRECISION NOT NULL
        DEFAULT 0,

    minimum_order_quantity DOUBLE PRECISION NOT NULL
        DEFAULT 0,

    case_pack_size DOUBLE PRECISION NOT NULL
        DEFAULT 1,

    target_service_level DOUBLE PRECISION NOT NULL
        DEFAULT 0.95,

    planning_horizon_days INTEGER NOT NULL
        DEFAULT 21,

    supplier_unit_cost DOUBLE PRECISION,

    on_time_delivery_rate DOUBLE PRECISION,

    active_flag BOOLEAN NOT NULL
        DEFAULT TRUE,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_scenario_supplier_policy
        PRIMARY KEY (
            store_id,
            product_id,
            supplier_id
        ),

    CONSTRAINT ck_supplier_lead_time_positive
        CHECK (
            average_lead_time_days > 0
        ),

    CONSTRAINT ck_supplier_lead_time_std_nonnegative
        CHECK (
            lead_time_std_days >= 0
        ),

    CONSTRAINT ck_supplier_moq_nonnegative
        CHECK (
            minimum_order_quantity >= 0
        ),

    CONSTRAINT ck_supplier_case_pack_positive
        CHECK (
            case_pack_size > 0
        ),

    CONSTRAINT ck_supplier_service_level
        CHECK (
            target_service_level > 0
            AND target_service_level < 1
        ),

    CONSTRAINT ck_supplier_planning_horizon_positive
        CHECK (
            planning_horizon_days > 0
        ),

    CONSTRAINT ck_supplier_otd_rate
        CHECK (
            on_time_delivery_rate IS NULL
            OR (
                on_time_delivery_rate >= 0
                AND on_time_delivery_rate <= 1
            )
        )
);


-- 3. BUSINESS PRIORITY

CREATE TABLE IF NOT EXISTS scenario.product_priority (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,

    stockout_cost_per_unit DOUBLE PRECISION,

    holding_cost_per_unit_day DOUBLE PRECISION,

    shelf_life_days INTEGER,

    working_capital_limit DOUBLE PRECISION,

    priority_weight DOUBLE PRECISION NOT NULL
        DEFAULT 1.0,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_scenario_product_priority
        PRIMARY KEY (
            store_id,
            product_id
        ),

    CONSTRAINT ck_stockout_cost_nonnegative
        CHECK (
            stockout_cost_per_unit IS NULL
            OR stockout_cost_per_unit >= 0
        ),

    CONSTRAINT ck_holding_cost_nonnegative
        CHECK (
            holding_cost_per_unit_day IS NULL
            OR holding_cost_per_unit_day >= 0
        ),

    CONSTRAINT ck_shelf_life_positive
        CHECK (
            shelf_life_days IS NULL
            OR shelf_life_days > 0
        ),

    CONSTRAINT ck_working_capital_nonnegative
        CHECK (
            working_capital_limit IS NULL
            OR working_capital_limit >= 0
        ),

    CONSTRAINT ck_priority_weight_positive
        CHECK (
            priority_weight > 0
        )
);