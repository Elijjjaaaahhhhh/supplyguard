-- One operational row per store-product decision.

-- Combines:
-- demand signal
-- inventory position
-- supplier risk
-- reorder requirement
-- constrained recommendation
-- urgency score
-- shared-capital allocation
-- final operational status


CREATE TABLE IF NOT EXISTS mart.control_tower (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    -- Demand
    expected_daily_demand DOUBLE PRECISION NOT NULL,
    demand_std DOUBLE PRECISION NOT NULL,

    -- Inventory / coverage
    on_hand_quantity DOUBLE PRECISION NOT NULL,
    on_order_quantity DOUBLE PRECISION NOT NULL,
    backorder_quantity DOUBLE PRECISION NOT NULL,
    inventory_position DOUBLE PRECISION NOT NULL,

    days_of_supply DOUBLE PRECISION,
    average_lead_time_days DOUBLE PRECISION NOT NULL,
    coverage_gap_days DOUBLE PRECISION,

    -- Inventory policy
    safety_stock DOUBLE PRECISION NOT NULL,
    reorder_point DOUBLE PRECISION NOT NULL,
    reorder_required BOOLEAN NOT NULL,

    raw_order_quantity DOUBLE PRECISION NOT NULL,
    final_recommended_quantity DOUBLE PRECISION NOT NULL,

    -- Constraints
    capital_constrained BOOLEAN NOT NULL,
    capacity_constrained BOOLEAN NOT NULL,
    shelf_life_constrained BOOLEAN NOT NULL,

    -- Risk
    urgency_score DOUBLE PRECISION,
    urgency_band TEXT,

    stockout_cost_per_unit DOUBLE PRECISION,
    on_time_delivery_rate DOUBLE PRECISION,
    priority_weight DOUBLE PRECISION NOT NULL,

    -- Shared capital allocation
    allocated_quantity DOUBLE PRECISION NOT NULL,
    allocated_order_value DOUBLE PRECISION NOT NULL,
    funding_status TEXT NOT NULL,

    -- Final control-tower decision
    control_tower_status TEXT NOT NULL,
    recommended_action TEXT NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_control_tower
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);


TRUNCATE TABLE mart.control_tower;


WITH base AS (
    SELECT
        d.store_id,
        d.product_id,
        d.decision_date,

        d.expected_daily_demand,
        d.demand_std,

        d.on_hand_quantity,
        d.on_order_quantity,
        d.backorder_quantity,
        d.inventory_position,

        d.days_of_supply,
        d.average_lead_time_days,
        d.coverage_gap_days,

        d.safety_stock,
        d.reorder_point,
        d.reorder_required,

        d.raw_order_quantity,

        r.final_recommended_quantity,

        r.capital_constrained,
        r.capacity_constrained,
        r.shelf_life_constrained,

        p.urgency_score,
        p.urgency_band,

        d.stockout_cost_per_unit,

        s.on_time_delivery_rate,

        d.priority_weight,

        COALESCE(
            a.allocated_quantity,
            0
        ) AS allocated_quantity,

        COALESCE(
            a.allocated_order_value,
            0
        ) AS allocated_order_value,

        CASE
            WHEN d.reorder_required = FALSE
                THEN 'NOT REQUIRED'

            WHEN a.funding_status IS NOT NULL
                THEN a.funding_status

            WHEN r.final_recommended_quantity <= 0
                THEN 'BLOCKED'

            ELSE 'UNFUNDED'
        END AS funding_status

    FROM mart.inventory_decision AS d

    JOIN mart.order_recommendation AS r
        ON d.store_id = r.store_id
    AND d.product_id = r.product_id
    AND d.decision_date = r.decision_date

    LEFT JOIN mart.priority_scored_order AS p
        ON d.store_id = p.store_id
    AND d.product_id = p.product_id
    AND d.decision_date = p.decision_date

    LEFT JOIN mart.procurement_capital_allocation AS a
        ON d.store_id = a.store_id
    AND d.product_id = a.product_id
    AND d.decision_date = a.decision_date

    JOIN scenario.supplier_policy AS s
        ON d.store_id = s.store_id
    AND d.product_id = s.product_id
    AND d.supplier_id = s.supplier_id
),


classified AS (
    SELECT
        *,

        CASE
            -- Highest priority:
            -- urgent + funded
            WHEN reorder_required = TRUE
            AND urgency_band = 'CRITICAL'
            AND allocated_quantity > 0
                THEN 'CRITICAL - ORDER NOW'


            WHEN reorder_required = TRUE
            AND urgency_band = 'HIGH'
            AND allocated_quantity > 0
                THEN 'HIGH - ORDER NOW'


            -- Urgent but not funded
            WHEN reorder_required = TRUE
            AND urgency_band IN (
                    'CRITICAL',
                    'HIGH'
                )
            AND allocated_quantity = 0
                THEN 'CRITICAL - FUNDING ESCALATION'


            -- Reorder needed but blocked by constraints
            WHEN reorder_required = TRUE
            AND final_recommended_quantity <= 0
                THEN 'CONSTRAINED - ESCALATE'


            -- Reorder needed but procurement-valid quantity
            -- still has no shared-capital allocation
            WHEN reorder_required = TRUE
            AND allocated_quantity = 0
                THEN 'REORDER - UNFUNDED'


            -- Medium / low priority funded requirement
            WHEN reorder_required = TRUE
            AND allocated_quantity > 0
                THEN 'REORDER - FUNDED'


            -- No reorder yet, but physical coverage is getting
            -- close to lead time.
            WHEN reorder_required = FALSE
            AND days_of_supply
                <= average_lead_time_days + 3
                THEN 'WATCH'


            ELSE 'HEALTHY'

        END AS control_tower_status

    FROM base
),


actioned AS (
    SELECT
        *,

        CASE
            WHEN control_tower_status
                = 'CRITICAL - ORDER NOW'
                THEN
                    'Place replenishment order immediately'

            WHEN control_tower_status
                = 'HIGH - ORDER NOW'
                THEN
                    'Place replenishment order'

            WHEN control_tower_status
                = 'CRITICAL - FUNDING ESCALATION'
                THEN
                    'Escalate working-capital request'

            WHEN control_tower_status
                = 'CONSTRAINED - ESCALATE'
                THEN
                    'Review MOQ, capacity, capital or shelf-life constraint'

            WHEN control_tower_status
                = 'REORDER - UNFUNDED'
                THEN
                    'Hold in funding queue and review priority'

            WHEN control_tower_status
                = 'REORDER - FUNDED'
                THEN
                    'Proceed with funded replenishment'

            WHEN control_tower_status
                = 'WATCH'
                THEN
                    'Monitor inventory coverage closely'

            ELSE
                'No immediate replenishment action'

        END AS recommended_action

    FROM classified
)


INSERT INTO mart.control_tower (
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
)

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

FROM actioned;