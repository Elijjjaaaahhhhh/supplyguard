
-- Converts raw replenishment quantities into operationally
-- feasible recommendations by applying:
-- 1. Minimum order quantity
-- 2. Case-pack rounding
-- 3. Working-capital limits
-- 4. Warehouse-capacity limits
-- 5. Shelf-life guardrails


CREATE TABLE IF NOT EXISTS mart.order_recommendation (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    reorder_required BOOLEAN NOT NULL,

    raw_order_quantity DOUBLE PRECISION NOT NULL,

    minimum_order_quantity DOUBLE PRECISION NOT NULL,
    case_pack_size DOUBLE PRECISION NOT NULL,

    unconstrained_pack_quantity DOUBLE PRECISION NOT NULL,

    supplier_unit_cost DOUBLE PRECISION,

    unconstrained_order_value DOUBLE PRECISION,

    affordable_quantity DOUBLE PRECISION,

    capacity_feasible_quantity DOUBLE PRECISION,

    shelf_life_max_quantity DOUBLE PRECISION,

    final_recommended_quantity DOUBLE PRECISION NOT NULL,

    final_order_value DOUBLE PRECISION,

    unmet_requirement_quantity DOUBLE PRECISION NOT NULL,

    capital_constrained BOOLEAN NOT NULL,
    capacity_constrained BOOLEAN NOT NULL,
    shelf_life_constrained BOOLEAN NOT NULL,

    recommendation_status TEXT NOT NULL,

    priority_weight DOUBLE PRECISION NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_order_recommendation
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);


TRUNCATE TABLE mart.order_recommendation;


WITH base AS (
    SELECT
        d.*,

        s.supplier_unit_cost

    FROM mart.inventory_decision AS d

    JOIN scenario.supplier_policy AS s
        ON d.store_id = s.store_id
    AND d.product_id = s.product_id
    AND d.supplier_id = s.supplier_id
),


pack_rounding AS (
    SELECT
        *,

        CASE
            WHEN reorder_required = FALSE
                THEN 0

            ELSE
                CEIL(
                    GREATEST(
                        raw_order_quantity,
                        minimum_order_quantity
                    )
                    /
                    case_pack_size
                )
                *
                case_pack_size
        END AS unconstrained_pack_quantity

    FROM base
),


capital_limit AS (
    SELECT
        *,

        unconstrained_pack_quantity
        *
        supplier_unit_cost
        AS unconstrained_order_value,


        CASE
            WHEN supplier_unit_cost IS NULL
                OR supplier_unit_cost <= 0
                OR working_capital_limit IS NULL
                THEN unconstrained_pack_quantity

            ELSE
                FLOOR(
                    working_capital_limit
                    /
                    supplier_unit_cost
                    /
                    case_pack_size
                )
                *
                case_pack_size
        END AS affordable_quantity

    FROM pack_rounding
),


capacity_limit AS (
    SELECT
        *,

        CASE
            WHEN warehouse_capacity_remaining IS NULL
                THEN unconstrained_pack_quantity

            ELSE
                FLOOR(
                    warehouse_capacity_remaining
                    /
                    case_pack_size
                )
                *
                case_pack_size
        END AS capacity_feasible_quantity

    FROM capital_limit
),


shelf_life_limit AS (
    SELECT
        *,

        CASE
            WHEN shelf_life_days IS NULL
                THEN unconstrained_pack_quantity

            /*
            Conservative rule:
            do not recommend inventory above expected demand
            over shelf life, after accounting for inventory
            already available.
            */

            ELSE
                GREATEST(
                    FLOOR(
                        (
                            expected_daily_demand
                            * shelf_life_days
                            - inventory_position
                        )
                        /
                        case_pack_size
                    )
                    *
                    case_pack_size,
                    0
                )
        END AS shelf_life_max_quantity

    FROM capacity_limit
),


final_math AS (
    SELECT
        *,

        CASE
            WHEN reorder_required = FALSE
                THEN 0

            ELSE
                GREATEST(
                    LEAST(
                        unconstrained_pack_quantity,
                        affordable_quantity,
                        capacity_feasible_quantity,
                        shelf_life_max_quantity
                    ),
                    0
                )
        END AS final_recommended_quantity

    FROM shelf_life_limit
)


INSERT INTO mart.order_recommendation (
    store_id,
    product_id,
    decision_date,

    reorder_required,

    raw_order_quantity,

    minimum_order_quantity,
    case_pack_size,

    unconstrained_pack_quantity,

    supplier_unit_cost,

    unconstrained_order_value,

    affordable_quantity,

    capacity_feasible_quantity,

    shelf_life_max_quantity,

    final_recommended_quantity,

    final_order_value,

    unmet_requirement_quantity,

    capital_constrained,
    capacity_constrained,
    shelf_life_constrained,

    recommendation_status,

    priority_weight
)

SELECT
    store_id,
    product_id,
    decision_date,

    reorder_required,

    raw_order_quantity,

    minimum_order_quantity,
    case_pack_size,

    unconstrained_pack_quantity,

    supplier_unit_cost,

    unconstrained_order_value,

    affordable_quantity,

    capacity_feasible_quantity,

    shelf_life_max_quantity,

    final_recommended_quantity,

    final_recommended_quantity
    *
    supplier_unit_cost
    AS final_order_value,

    GREATEST(
        raw_order_quantity
        - final_recommended_quantity,
        0
    ) AS unmet_requirement_quantity,


    (
        affordable_quantity
        <
        unconstrained_pack_quantity
    ) AS capital_constrained,


    (
        capacity_feasible_quantity
        <
        unconstrained_pack_quantity
    ) AS capacity_constrained,


    (
        shelf_life_max_quantity
        <
        unconstrained_pack_quantity
    ) AS shelf_life_constrained,


    CASE
        WHEN reorder_required = FALSE
            THEN 'NO ORDER REQUIRED'

        WHEN final_recommended_quantity <= 0
            THEN 'BLOCKED BY CONSTRAINTS'

        WHEN final_recommended_quantity
            < raw_order_quantity
            THEN 'PARTIALLY CONSTRAINED'

        WHEN final_recommended_quantity
            >= raw_order_quantity
            THEN 'ORDER RECOMMENDED'

        ELSE 'REVIEW'
    END AS recommendation_status,

    priority_weight

FROM final_math;