-- 1. Enforces minimum order quantity (MOQ)
-- 2. Enforces whole case-pack quantities
-- 3. Never allocates fractional units
-- 4. Never allocates arbitrary partial currency amounts
-- 5. Uses urgency ranking
-- 6. Tracks unused shared budget

-- Allocation approach:
-- Greedy priority allocation.

-- Highest-urgency orders are considered first.
-- Each order receives as many complete case packs as the
-- remaining shared budget can support, subject to MOQ.

-- Scenario shared budget = 50,000 currency units.


CREATE TABLE IF NOT EXISTS mart.procurement_capital_allocation (
    priority_rank INTEGER NOT NULL,

    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    urgency_score DOUBLE PRECISION NOT NULL,
    urgency_band TEXT NOT NULL,

    minimum_order_quantity DOUBLE PRECISION NOT NULL,
    case_pack_size DOUBLE PRECISION NOT NULL,
    supplier_unit_cost DOUBLE PRECISION NOT NULL,

    requested_quantity DOUBLE PRECISION NOT NULL,
    requested_order_value DOUBLE PRECISION NOT NULL,

    allocated_quantity DOUBLE PRECISION NOT NULL,
    allocated_order_value DOUBLE PRECISION NOT NULL,

    unmet_quantity_after_allocation DOUBLE PRECISION NOT NULL,

    funding_status TEXT NOT NULL,

    budget_before_order DOUBLE PRECISION NOT NULL,
    budget_after_order DOUBLE PRECISION NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_procurement_capital_allocation
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);


TRUNCATE TABLE mart.procurement_capital_allocation;


WITH RECURSIVE


-- STEP 1
-- Identify recommendations that are actually procurement-valid.

-- Here we additionally require it to satisfy MOQ.

eligible_orders AS (
    SELECT
        ROW_NUMBER() OVER (
            ORDER BY
                p.urgency_score DESC,
                p.store_id,
                p.product_id
        )::INTEGER AS priority_rank,

        p.store_id,
        p.product_id,
        p.decision_date,

        p.urgency_score,
        p.urgency_band,

        r.minimum_order_quantity,
        r.case_pack_size,
        r.supplier_unit_cost,

        r.final_recommended_quantity
            AS requested_quantity,

        (
            r.final_recommended_quantity
            * r.supplier_unit_cost
        ) AS requested_order_value

    FROM mart.priority_scored_order AS p

    JOIN mart.order_recommendation AS r
        ON p.store_id = r.store_id
       AND p.product_id = r.product_id
       AND p.decision_date = r.decision_date

    WHERE
        r.reorder_required = TRUE

        AND r.final_recommended_quantity > 0

        AND r.supplier_unit_cost IS NOT NULL
        AND r.supplier_unit_cost > 0

        -- Procurement validity:
        -- final quantity must meet supplier MOQ.
        AND r.final_recommended_quantity
            >= r.minimum_order_quantity
),


-- STEP 2
-- Recursive greedy allocation.

-- Start with 50,000.
--
-- For each order:
-- - calculate how many whole packs remaining budget can buy
-- - never exceed requested quantity
-- - only fund if resulting quantity still meets MOQ

allocation AS (

    -- --------------------------------------------------------
    -- First priority order
    -- --------------------------------------------------------

    SELECT
        e.priority_rank,

        e.store_id,
        e.product_id,
        e.decision_date,

        e.urgency_score,
        e.urgency_band,

        e.minimum_order_quantity,
        e.case_pack_size,
        e.supplier_unit_cost,

        e.requested_quantity,
        e.requested_order_value,

        50000.0::DOUBLE PRECISION
            AS budget_before_order,


        CASE
            WHEN
                LEAST(
                    e.requested_quantity,

                    FLOOR(
                        50000.0
                        /
                        (
                            e.case_pack_size
                            * e.supplier_unit_cost
                        )
                    )
                    * e.case_pack_size
                )
                >= e.minimum_order_quantity

            THEN
                LEAST(
                    e.requested_quantity,

                    FLOOR(
                        50000.0
                        /
                        (
                            e.case_pack_size
                            * e.supplier_unit_cost
                        )
                    )
                    * e.case_pack_size
                )

            ELSE 0
        END::DOUBLE PRECISION
            AS allocated_quantity

    FROM eligible_orders AS e

    WHERE e.priority_rank = 1


    UNION ALL


    -- --------------------------------------------------------
    -- Remaining priority orders
    -- --------------------------------------------------------

    SELECT
        e.priority_rank,

        e.store_id,
        e.product_id,
        e.decision_date,

        e.urgency_score,
        e.urgency_band,

        e.minimum_order_quantity,
        e.case_pack_size,
        e.supplier_unit_cost,

        e.requested_quantity,
        e.requested_order_value,

        GREATEST(
            a.budget_before_order
            -
            (
                a.allocated_quantity
                * a.supplier_unit_cost
            ),
            0
        ) AS budget_before_order,


        CASE
            WHEN
                LEAST(
                    e.requested_quantity,

                    FLOOR(
                        GREATEST(
                            a.budget_before_order
                            -
                            (
                                a.allocated_quantity
                                * a.supplier_unit_cost
                            ),
                            0
                        )
                        /
                        (
                            e.case_pack_size
                            * e.supplier_unit_cost
                        )
                    )
                    * e.case_pack_size
                )
                >= e.minimum_order_quantity

            THEN
                LEAST(
                    e.requested_quantity,

                    FLOOR(
                        GREATEST(
                            a.budget_before_order
                            -
                            (
                                a.allocated_quantity
                                * a.supplier_unit_cost
                            ),
                            0
                        )
                        /
                        (
                            e.case_pack_size
                            * e.supplier_unit_cost
                        )
                    )
                    * e.case_pack_size
                )

            ELSE 0
        END::DOUBLE PRECISION
            AS allocated_quantity

    FROM allocation AS a

    JOIN eligible_orders AS e
        ON e.priority_rank
        = a.priority_rank + 1
),


-- ============================================================
-- STEP 3
-- Calculate values and remaining budget.
-- ============================================================

final_allocation AS (
    SELECT
        *,

        (
            allocated_quantity
            * supplier_unit_cost
        ) AS allocated_order_value,

        GREATEST(
            requested_quantity
            - allocated_quantity,
            0
        ) AS unmet_quantity_after_allocation,

        GREATEST(
            budget_before_order
            -
            (
                allocated_quantity
                * supplier_unit_cost
            ),
            0
        ) AS budget_after_order

    FROM allocation
)


-- STEP 4
-- Persist results.

INSERT INTO mart.procurement_capital_allocation (
    priority_rank,

    store_id,
    product_id,
    decision_date,

    urgency_score,
    urgency_band,

    minimum_order_quantity,
    case_pack_size,
    supplier_unit_cost,

    requested_quantity,
    requested_order_value,

    allocated_quantity,
    allocated_order_value,

    unmet_quantity_after_allocation,

    funding_status,

    budget_before_order,
    budget_after_order
)

SELECT
    priority_rank,

    store_id,
    product_id,
    decision_date,

    urgency_score,
    urgency_band,

    minimum_order_quantity,
    case_pack_size,
    supplier_unit_cost,

    requested_quantity,
    requested_order_value,

    allocated_quantity,
    allocated_order_value,

    unmet_quantity_after_allocation,

    CASE
        WHEN allocated_quantity = 0
            THEN 'UNFUNDED'

        WHEN allocated_quantity
            < requested_quantity
            THEN 'PARTIALLY FUNDED'

        ELSE 'FULLY FUNDED'
    END AS funding_status,

    budget_before_order,
    budget_after_order

FROM final_allocation;