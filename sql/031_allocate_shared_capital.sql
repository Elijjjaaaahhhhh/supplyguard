-- Allocates a simulated shared replenishment budget in
-- descending urgency order.

-- Prototype budget: 50,000 currency units.


CREATE TABLE IF NOT EXISTS mart.capital_allocation (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    urgency_score DOUBLE PRECISION NOT NULL,
    urgency_band TEXT NOT NULL,

    requested_order_quantity DOUBLE PRECISION NOT NULL,
    requested_order_value DOUBLE PRECISION NOT NULL,

    allocated_order_quantity DOUBLE PRECISION NOT NULL,
    allocated_order_value DOUBLE PRECISION NOT NULL,

    funding_status TEXT NOT NULL,

    cumulative_budget_used DOUBLE PRECISION NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_capital_allocation
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);


TRUNCATE TABLE mart.capital_allocation;


WITH eligible AS (
    SELECT
        p.*,

        COALESCE(
            p.final_order_value,
            0
        ) AS requested_value,

        ROW_NUMBER() OVER (
            ORDER BY
                p.urgency_score DESC,
                p.store_id,
                p.product_id
        ) AS priority_rank

    FROM mart.priority_scored_order AS p

    WHERE p.final_recommended_quantity > 0
),


running AS (
    SELECT
        *,

        SUM(requested_value) OVER (
            ORDER BY priority_rank
            ROWS BETWEEN
                UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS cumulative_requested_value

    FROM eligible
),


allocated AS (
    SELECT
        *,

        50000.0 AS total_budget,

        CASE
            WHEN cumulative_requested_value <= 50000.0
                THEN requested_value

            WHEN cumulative_requested_value - requested_value
                >= 50000.0
                THEN 0

            ELSE
                50000.0
                - (
                    cumulative_requested_value
                    - requested_value
                )
        END AS allocated_value

    FROM running
),


quantity_calc AS (
    SELECT
        *,

        CASE
            WHEN requested_value <= 0
                THEN 0

            ELSE
                final_recommended_quantity
                *
                (
                    allocated_value
                    /
                    requested_value
                )
        END AS allocated_quantity

    FROM allocated
)


INSERT INTO mart.capital_allocation (
    store_id,
    product_id,
    decision_date,

    urgency_score,
    urgency_band,

    requested_order_quantity,
    requested_order_value,

    allocated_order_quantity,
    allocated_order_value,

    funding_status,

    cumulative_budget_used
)

SELECT
    store_id,
    product_id,
    decision_date,

    urgency_score,
    urgency_band,

    final_recommended_quantity,
    requested_value,

    allocated_quantity,
    allocated_value,

    CASE
        WHEN allocated_value = 0
            THEN 'UNFUNDED'

        WHEN allocated_value < requested_value
            THEN 'PARTIALLY FUNDED'

        ELSE 'FULLY FUNDED'
    END,

    LEAST(
        cumulative_requested_value,
        total_budget
    )

FROM quantity_calc;