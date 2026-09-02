import os
from datetime import timedelta

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()


RANDOM_SEED = 42
SAMPLE_SIZE = 1000
AS_OF_DATE = pd.Timestamp("2024-07-02")


def get_engine():
    """
    Create PostgreSQL SQLAlchemy engine.
    """
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(
            os.getenv(
                "DB_PORT",
                "5432",
            )
        ),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(url)


def load_series_profiles(
    engine,
) -> pd.DataFrame:
    """
    Build one profile row per store-product series
    using real historical demand behaviour.
    """
    query = """
        SELECT
            store_id,
            product_id,

            AVG(sale_amount) AS mean_daily_demand,

            STDDEV_SAMP(
                sale_amount
            ) AS demand_std,

            MAX(sale_amount) AS max_daily_demand,

            AVG(stockout_hours) AS avg_stockout_hours,

            COUNT(*) FILTER (
                WHERE sale_amount = 0
            )::DOUBLE PRECISION
            / COUNT(*) AS zero_sales_fraction

        FROM core.fact_daily_demand

        WHERE source_file = 'train.parquet'

        GROUP BY
            store_id,
            product_id
    """

    return pd.read_sql(
        query,
        engine,
    )


def select_representative_series(
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """
    Select a mixture of high-volume, volatile
    and normal store-product series.
    """
    profiles = profiles.copy()

    profiles["cv"] = (
        profiles["demand_std"]
        / profiles["mean_daily_demand"]
            .replace(0, np.nan)
    )

    profiles["volume_rank"] = (
        profiles["mean_daily_demand"]
        .rank(
            pct=True,
            method="average",
        )
    )

    profiles["volatility_rank"] = (
        profiles["cv"]
        .rank(
            pct=True,
            method="average",
        )
    )

    high_volume = (
        profiles
        .sort_values(
            "mean_daily_demand",
            ascending=False,
        )
        .head(250)
    )

    high_volatility = (
        profiles
        .sort_values(
            "cv",
            ascending=False,
        )
        .head(250)
    )

    remaining = profiles.drop(
        index=high_volume.index.union(
            high_volatility.index
        ),
        errors="ignore",
    )

    random_sample = remaining.sample(
        n=500,
        random_state=RANDOM_SEED,
    )

    selected = pd.concat(
        [
            high_volume,
            high_volatility,
            random_sample,
        ],
        ignore_index=True,
    )

    selected = (
        selected
        .drop_duplicates(
            subset=[
                "store_id",
                "product_id",
            ]
        )
    )

    if len(selected) < SAMPLE_SIZE:

        missing = (
            SAMPLE_SIZE
            - len(selected)
        )

        already_selected = set(
            zip(
                selected["store_id"],
                selected["product_id"],
            )
        )

        available = profiles[
            ~profiles.apply(
                lambda row: (
                    row["store_id"],
                    row["product_id"],
                )
                in already_selected,
                axis=1,
            )
        ]

        top_up = available.sample(
            n=missing,
            random_state=RANDOM_SEED + 1,
        )

        selected = pd.concat(
            [
                selected,
                top_up,
            ],
            ignore_index=True,
        )

    return selected.head(
        SAMPLE_SIZE
    ).reset_index(drop=True)


def derive_service_level(
    cv: float,
    mean_daily_demand: float,
) -> float:
    """
    Assign a plausible service level based on
    demand importance and volatility.

    These are scenario assumptions, not source facts.
    """
    if mean_daily_demand >= 2.0:
        return 0.99

    if cv >= 1.5:
        return 0.975

    if mean_daily_demand >= 1.0:
        return 0.975

    return 0.95


def generate_inventory_positions(
    selected: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic current inventory state.
    """
    rows = []

    for row in selected.itertuples():

        mean_demand = max(
            float(row.mean_daily_demand),
            0.05,
        )

        # Simulate roughly 4-18 days of physical stock.
        days_on_hand = rng.uniform(
            4,
            18,
        )

        on_hand = (
            mean_demand
            * days_on_hand
        )

        # Some products have inventory already on order.
        if rng.random() < 0.55:
            on_order = (
                mean_demand
                * rng.uniform(
                    2,
                    10,
                )
            )
        else:
            on_order = 0.0

        # Backorders are less common.
        if rng.random() < 0.15:
            backorder = (
                mean_demand
                * rng.uniform(
                    0.5,
                    3,
                )
            )
        else:
            backorder = 0.0

        if on_order > 0:
            receipt_days = int(
                rng.integers(
                    2,
                    15,
                )
            )

            receipt_date = (
                AS_OF_DATE
                + timedelta(
                    days=receipt_days
                )
            ).date()
        else:
            receipt_date = None

        # Synthetic unit cost.
        unit_cost = rng.uniform(
            5,
            150,
        )

        # Capacity remaining is tied loosely
        # to expected stock requirement.
        capacity_remaining = (
            mean_demand
            * rng.uniform(
                10,
                40,
            )
        )

        rows.append(
            {
                "store_id": int(
                    row.store_id
                ),
                "product_id": int(
                    row.product_id
                ),
                "as_of_date": AS_OF_DATE.date(),

                "on_hand_quantity": round(
                    on_hand,
                    2,
                ),

                "on_order_quantity": round(
                    on_order,
                    2,
                ),

                "backorder_quantity": round(
                    backorder,
                    2,
                ),

                "expected_next_receipt_date": (
                    receipt_date
                ),

                "unit_cost": round(
                    unit_cost,
                    2,
                ),

                "warehouse_capacity_remaining": round(
                    capacity_remaining,
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


def generate_supplier_policies(
    selected: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic supplier lead-time
    and replenishment policy data.
    """
    rows = []

    for row in selected.itertuples():

        mean_demand = max(
            float(row.mean_daily_demand),
            0.05,
        )

        cv = (
            float(row.cv)
            if pd.notna(row.cv)
            else 0.0
        )

        average_lead_time = rng.uniform(
            5,
            14,
        )

        lead_time_std = rng.uniform(
            0.5,
            3.0,
        )

        service_level = (
            derive_service_level(
                cv=cv,
                mean_daily_demand=mean_demand,
            )
        )

        minimum_order_quantity = max(
            1.0,
            mean_demand
            * rng.uniform(
                3,
                10,
            ),
        )

        case_pack_size = float(
            rng.choice(
                [
                    1,
                    6,
                    12,
                    24,
                ]
            )
        )

        planning_horizon = int(
            rng.choice(
                [
                    21,
                    28,
                ]
            )
        )

        supplier_unit_cost = rng.uniform(
            5,
            140,
        )

        on_time_delivery_rate = rng.uniform(
            0.80,
            0.99,
        )

        supplier_id = (
            int(row.product_id)
            % 25
        ) + 1

        rows.append(
            {
                "store_id": int(
                    row.store_id
                ),

                "product_id": int(
                    row.product_id
                ),

                "supplier_id": supplier_id,

                "average_lead_time_days": round(
                    average_lead_time,
                    2,
                ),

                "lead_time_std_days": round(
                    lead_time_std,
                    2,
                ),

                "minimum_order_quantity": round(
                    minimum_order_quantity,
                    2,
                ),

                "case_pack_size": case_pack_size,

                "target_service_level": (
                    service_level
                ),

                "planning_horizon_days": (
                    planning_horizon
                ),

                "supplier_unit_cost": round(
                    supplier_unit_cost,
                    2,
                ),

                "on_time_delivery_rate": round(
                    on_time_delivery_rate,
                    4,
                ),

                "active_flag": True,
            }
        )

    return pd.DataFrame(rows)


def generate_product_priorities(
    selected: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Create synthetic economic and business-priority inputs.
    """
    rows = []

    for row in selected.itertuples():

        mean_demand = max(
            float(row.mean_daily_demand),
            0.05,
        )

        cv = (
            float(row.cv)
            if pd.notna(row.cv)
            else 0.0
        )

        stockout_cost = rng.uniform(
            10,
            250,
        )

        holding_cost = rng.uniform(
            0.01,
            1.50,
        )

        # Some products are treated as perishable.
        if rng.random() < 0.30:
            shelf_life_days = int(
                rng.integers(
                    14,
                    180,
                )
            )
        else:
            shelf_life_days = None

        working_capital_limit = (
            mean_demand
            * rng.uniform(
                100,
                600,
            )
        )

        priority_weight = (
            1.0
            + min(
                mean_demand / 5,
                1.5,
            )
            + min(
                cv / 3,
                1.0,
            )
        )

        rows.append(
            {
                "store_id": int(
                    row.store_id
                ),

                "product_id": int(
                    row.product_id
                ),

                "stockout_cost_per_unit": round(
                    stockout_cost,
                    2,
                ),

                "holding_cost_per_unit_day": round(
                    holding_cost,
                    4,
                ),

                "shelf_life_days": (
                    shelf_life_days
                ),

                "working_capital_limit": round(
                    working_capital_limit,
                    2,
                ),

                "priority_weight": round(
                    priority_weight,
                    4,
                ),
            }
        )

    return pd.DataFrame(rows)


def write_scenario_tables(
    engine,
    inventory_df: pd.DataFrame,
    supplier_df: pd.DataFrame,
    priority_df: pd.DataFrame,
) -> None:
    """
    Replace scenario data for this development run.

    This is acceptable because the scenario schema
    contains synthetic development inputs.
    """
    with engine.begin() as connection:

        connection.exec_driver_sql(
            """
            TRUNCATE TABLE
                scenario.inventory_position,
                scenario.supplier_policy,
                scenario.product_priority
            """
        )

    inventory_df.to_sql(
        name="inventory_position",
        con=engine,
        schema="scenario",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    supplier_df.to_sql(
        name="supplier_policy",
        con=engine,
        schema="scenario",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    priority_df.to_sql(
        name="product_priority",
        con=engine,
        schema="scenario",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )


def main():
    rng = np.random.default_rng(
        RANDOM_SEED
    )

    engine = get_engine()

    try:
        print(
            "\nLoading real store-product demand profiles..."
        )

        profiles = load_series_profiles(
            engine
        )

        print(
            f"Available series: "
            f"{len(profiles):,}"
        )

        selected = (
            select_representative_series(
                profiles
            )
        )

        print(
            f"Selected scenario series: "
            f"{len(selected):,}"
        )

        inventory_df = (
            generate_inventory_positions(
                selected,
                rng,
            )
        )

        supplier_df = (
            generate_supplier_policies(
                selected,
                rng,
            )
        )

        priority_df = (
            generate_product_priorities(
                selected,
                rng,
            )
        )

        print(
            "\nWriting scenario tables..."
        )

        write_scenario_tables(
            engine=engine,
            inventory_df=inventory_df,
            supplier_df=supplier_df,
            priority_df=priority_df,
        )

        print(
            "\nScenario generation complete."
        )

        print(
            f"Inventory rows: "
            f"{len(inventory_df):,}"
        )

        print(
            f"Supplier rows: "
            f"{len(supplier_df):,}"
        )

        print(
            f"Priority rows: "
            f"{len(priority_df):,}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()