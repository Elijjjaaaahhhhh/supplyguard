-- Builds replenishment decisions for the 1,000 simulated
-- operational scenarios.


TRUNCATE TABLE mart.inventory_decision;


WITH demand_profile AS (
    SELECT
        store_id,
        product_id,

        STDDEV_SAMP(
            sale_amount
        ) AS demand_std

    FROM core.fact_daily_demand

    WHERE source_file = 'train.parquet'

    GROUP BY
        store_id,
        product_id
),


latest_prediction AS (
    /*
    During the decision-engine prototype we use the most recent
    model prediction from the final evaluation output represented
    by the model feature layer.

    Because the CSV predictions are not yet stored in PostgreSQL,
    expected demand is approximated using the most recent
    historical rolling demand level.

    We will replace this with persisted model forecasts later.
    */

    SELECT DISTINCT ON (
        store_id,
        product_id
    )
        store_id,
        product_id,
        sales_rolling_mean_7
            AS expected_daily_demand

    FROM feature.v_demand_model_v3

    WHERE dt <= DATE '2024-07-02'

    ORDER BY
        store_id,
        product_id,
        dt DESC
),


joined_inputs AS (
    SELECT
        i.store_id,
        i.product_id,
        i.as_of_date
            AS decision_date,

        GREATEST(
            lp.expected_daily_demand,
            0.01
        ) AS expected_daily_demand,

        COALESCE(
            dp.demand_std,
            0
        ) AS demand_std,

        i.on_hand_quantity,
        i.on_order_quantity,
        i.backorder_quantity,

        (
            i.on_hand_quantity
            + i.on_order_quantity
            - i.backorder_quantity
        ) AS inventory_position,

        i.unit_cost,
        i.warehouse_capacity_remaining,

        s.supplier_id,
        s.average_lead_time_days,
        s.lead_time_std_days,
        s.minimum_order_quantity,
        s.case_pack_size,
        s.target_service_level,
        s.planning_horizon_days,

        p.stockout_cost_per_unit,
        p.holding_cost_per_unit_day,
        p.shelf_life_days,
        p.working_capital_limit,
        p.priority_weight,

        CASE
            WHEN s.target_service_level >= 0.99
                THEN 2.326

            WHEN s.target_service_level >= 0.975
                THEN 1.960

            ELSE 1.645
        END AS z_score

    FROM scenario.inventory_position AS i

    JOIN scenario.supplier_policy AS s
        ON i.store_id = s.store_id
    AND i.product_id = s.product_id
    AND s.active_flag = TRUE

    JOIN scenario.product_priority AS p
        ON i.store_id = p.store_id
    AND i.product_id = p.product_id

    JOIN demand_profile AS dp
        ON i.store_id = dp.store_id
    AND i.product_id = dp.product_id

    JOIN latest_prediction AS lp
        ON i.store_id = lp.store_id
    AND i.product_id = lp.product_id
),


inventory_math AS (
    SELECT
        *,

        -- Expected demand while waiting for replenishment.
        (
            expected_daily_demand
            * average_lead_time_days
        ) AS lead_time_demand,


        -- Safety stock allowing for BOTH:
        -- 1. demand uncertainty
        -- 2. supplier lead-time uncertainty
        (
            z_score
            *
            SQRT(
                (
                    average_lead_time_days
                    * POWER(
                        demand_std,
                        2
                    )
                )
                +
                (
                    POWER(
                        expected_daily_demand,
                        2
                    )
                    *
                    POWER(
                        lead_time_std_days,
                        2
                    )
                )
            )
        ) AS safety_stock,


        -- Physical stock coverage.
        CASE
            WHEN expected_daily_demand > 0
            THEN
                on_hand_quantity
                / expected_daily_demand

            ELSE NULL
        END AS days_of_supply

    FROM joined_inputs
),


decision_math AS (
    SELECT
        *,

        (
            lead_time_demand
            + safety_stock
        ) AS reorder_point,


        (
            expected_daily_demand
            * planning_horizon_days
            + safety_stock
        ) AS target_stock_level,


        GREATEST(
            average_lead_time_days
            - days_of_supply,
            0
        ) AS coverage_gap_days

    FROM inventory_math
),


final_decisions AS (
    SELECT
        *,

        (
            inventory_position
            <= reorder_point
        ) AS reorder_required,


        GREATEST(
            target_stock_level
            - inventory_position,
            0
        ) AS raw_order_quantity

    FROM decision_math
)


INSERT INTO mart.inventory_decision (
    store_id,
    product_id,
    decision_date,

    expected_daily_demand,
    demand_std,

    on_hand_quantity,
    on_order_quantity,
    backorder_quantity,
    inventory_position,

    supplier_id,
    average_lead_time_days,
    lead_time_std_days,
    target_service_level,
    planning_horizon_days,

    lead_time_demand,
    safety_stock,
    reorder_point,

    days_of_supply,
    coverage_gap_days,

    reorder_required,

    target_stock_level,
    raw_order_quantity,

    minimum_order_quantity,
    case_pack_size,
    unit_cost,
    working_capital_limit,
    warehouse_capacity_remaining,

    stockout_cost_per_unit,
    holding_cost_per_unit_day,
    shelf_life_days,
    priority_weight
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

    supplier_id,
    average_lead_time_days,
    lead_time_std_days,
    target_service_level,
    planning_horizon_days,

    lead_time_demand,
    safety_stock,
    reorder_point,

    days_of_supply,
    coverage_gap_days,

    reorder_required,

    target_stock_level,
    raw_order_quantity,

    minimum_order_quantity,
    case_pack_size,
    unit_cost,
    working_capital_limit,
    warehouse_capacity_remaining,

    stockout_cost_per_unit,
    holding_cost_per_unit_day,
    shelf_life_days,
    priority_weight

FROM final_decisions;