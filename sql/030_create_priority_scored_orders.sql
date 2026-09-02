-- Creates a transparent urgency score using:
-- - coverage gap
-- - stockout cost
-- - supplier reliability
-- - demand level
-- - business priority weight
-- - unmet requirement


CREATE TABLE IF NOT EXISTS mart.priority_scored_order (
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    decision_date DATE NOT NULL,

    recommendation_status TEXT NOT NULL,

    final_recommended_quantity DOUBLE PRECISION NOT NULL,
    final_order_value DOUBLE PRECISION,
    unmet_requirement_quantity DOUBLE PRECISION NOT NULL,

    expected_daily_demand DOUBLE PRECISION NOT NULL,
    coverage_gap_days DOUBLE PRECISION NOT NULL,

    stockout_cost_per_unit DOUBLE PRECISION,
    on_time_delivery_rate DOUBLE PRECISION,
    priority_weight DOUBLE PRECISION NOT NULL,

    urgency_score DOUBLE PRECISION NOT NULL,

    urgency_band TEXT NOT NULL,

    calculated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_priority_scored_order
        PRIMARY KEY (
            store_id,
            product_id,
            decision_date
        )
);


TRUNCATE TABLE mart.priority_scored_order;


WITH joined AS (
    SELECT
        r.store_id,
        r.product_id,
        r.decision_date,

        r.recommendation_status,

        r.final_recommended_quantity,
        r.final_order_value,
        r.unmet_requirement_quantity,

        d.expected_daily_demand,
        d.coverage_gap_days,

        d.stockout_cost_per_unit,
        d.priority_weight,

        s.on_time_delivery_rate

    FROM mart.order_recommendation AS r

    JOIN mart.inventory_decision AS d
        ON r.store_id = d.store_id
    AND r.product_id = d.product_id
    AND r.decision_date = d.decision_date

    JOIN scenario.supplier_policy AS s
        ON d.store_id = s.store_id
    AND d.product_id = s.product_id
    AND d.supplier_id = s.supplier_id

    WHERE r.reorder_required = TRUE
),


normalised AS (
    SELECT
        *,

        COALESCE(
            coverage_gap_days
            / NULLIF(
                MAX(coverage_gap_days) OVER (),
                0
            ),
            0
        ) AS coverage_gap_score,

        COALESCE(
            stockout_cost_per_unit
            / NULLIF(
                MAX(stockout_cost_per_unit) OVER (),
                0
            ),
            0
        ) AS stockout_cost_score,

        COALESCE(
            expected_daily_demand
            / NULLIF(
                MAX(expected_daily_demand) OVER (),
                0
            ),
            0
        ) AS demand_score,

        COALESCE(
            unmet_requirement_quantity
            / NULLIF(
                MAX(unmet_requirement_quantity) OVER (),
                0
            ),
            0
        ) AS unmet_requirement_score,

        COALESCE(
            1 - on_time_delivery_rate,
            0
        ) AS supplier_risk_score,

        COALESCE(
            priority_weight
            / NULLIF(
                MAX(priority_weight) OVER (),
                0
            ),
            0
        ) AS business_priority_score

    FROM joined
),


scored AS (
    SELECT
        *,

        (
            0.30 * coverage_gap_score
            +
            0.20 * stockout_cost_score
            +
            0.15 * demand_score
            +
            0.15 * unmet_requirement_score
            +
            0.10 * supplier_risk_score
            +
            0.10 * business_priority_score
        ) * 100
        AS urgency_score

    FROM normalised
)


INSERT INTO mart.priority_scored_order (
    store_id,
    product_id,
    decision_date,

    recommendation_status,

    final_recommended_quantity,
    final_order_value,
    unmet_requirement_quantity,

    expected_daily_demand,
    coverage_gap_days,

    stockout_cost_per_unit,
    on_time_delivery_rate,
    priority_weight,

    urgency_score,

    urgency_band
)

SELECT
    store_id,
    product_id,
    decision_date,

    recommendation_status,

    final_recommended_quantity,
    final_order_value,
    unmet_requirement_quantity,

    expected_daily_demand,
    coverage_gap_days,

    stockout_cost_per_unit,
    on_time_delivery_rate,
    priority_weight,

    urgency_score,

    CASE
        WHEN urgency_score >= 70
            THEN 'CRITICAL'

        WHEN urgency_score >= 50
            THEN 'HIGH'

        WHEN urgency_score >= 30
            THEN 'MEDIUM'

        ELSE 'LOW'
    END

FROM scored;