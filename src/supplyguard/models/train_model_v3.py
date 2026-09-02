import os
from time import perf_counter

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sklearn.ensemble import HistGradientBoostingRegressor
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()


FEATURE_COLUMNS = [
    "store_id",
    "product_id",
    "first_category_id",
    "second_category_id",
    "third_category_id",

    "day_of_week",
    "is_weekend",
    "holiday_flag",

    "sales_lag_1",
    "sales_lag_2",
    "sales_lag_3",
    "sales_lag_7",
    "sales_lag_14",

    "sales_rolling_mean_7",
    "sales_rolling_mean_14",
    "sales_rolling_mean_28",

    "sales_rolling_std_7",
    "sales_rolling_std_14",
    "sales_rolling_std_28",

    "sales_rolling_max_7",
    "sales_rolling_max_14",
    "sales_rolling_max_28",

    "recent_growth_7_vs_28",

    "stockout_lag_1",
    "stockout_rolling_mean_7",

    # V3 exogenous features
    "discount",
    "activity_flag",
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
]

TARGET_COLUMN = "target_sale_amount"


def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(url)


def load_dataset(
    engine,
    view_name: str,
) -> pd.DataFrame:
    columns = [
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    ]

    query = f"""
        SELECT
            {", ".join(columns)}
        FROM {view_name}
    """

    return pd.read_sql(
        query,
        engine,
    )


def mae(actual, predicted):
    return np.mean(
        np.abs(actual - predicted)
    )


def rmse(actual, predicted):
    return np.sqrt(
        np.mean(
            np.square(actual - predicted)
        )
    )


def wape(actual, predicted):
    denominator = np.sum(
        np.abs(actual)
    )

    if denominator == 0:
        return np.nan

    return (
        np.sum(
            np.abs(actual - predicted)
        )
        / denominator
    )


def evaluate(actual, predicted):
    return {
        "MAE": mae(actual, predicted),
        "RMSE": rmse(actual, predicted),
        "WAPE": wape(actual, predicted),
    }


def print_metrics(
    title: str,
    metrics: dict,
) -> None:
    print(
        f"\n--- {title} ---"
    )

    for metric, value in metrics.items():
        print(
            f"{metric}: {value:.4f}"
        )


def print_demand_band_diagnostics(
    actual,
    v3_predictions,
    rolling_predictions,
):
    diagnostics = pd.DataFrame(
        {
            "actual": actual,
            "v3_prediction": v3_predictions,
            "rolling_prediction": rolling_predictions,
        }
    )

    diagnostics["v3_absolute_error"] = (
        diagnostics["v3_prediction"]
        - diagnostics["actual"]
    ).abs()

    diagnostics["rolling_absolute_error"] = (
        diagnostics["rolling_prediction"]
        - diagnostics["actual"]
    ).abs()

    diagnostics["demand_band"] = pd.cut(
        diagnostics["actual"],
        bins=[
            -np.inf,
            0,
            0.5,
            1.0,
            2.0,
            np.inf,
        ],
        labels=[
            "Zero",
            "0-0.5",
            "0.5-1.0",
            "1.0-2.0",
            ">2.0",
        ],
    )

    summary = (
        diagnostics
        .groupby(
            "demand_band",
            observed=True,
        )
        .agg(
            observations=(
                "actual",
                "size",
            ),
            actual_mean=(
                "actual",
                "mean",
            ),
            v3_mae=(
                "v3_absolute_error",
                "mean",
            ),
            rolling_mae=(
                "rolling_absolute_error",
                "mean",
            ),
        )
        .reset_index()
    )

    print(
        "\n--- V3 ERROR BY ACTUAL DEMAND ---"
    )

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )


def main():
    engine = get_engine()

    try:
        print(
            "\nLoading V3 development training data..."
        )

        train_df = load_dataset(
            engine,
            "feature.v_demand_model_v3_dev_train",
        )

        print(
            f"Training rows: {len(train_df):,}"
        )

        print(
            "\nLoading V3 validation data..."
        )

        validation_df = load_dataset(
            engine,
            "feature.v_demand_model_v3_validation",
        )

        print(
            f"Validation rows: {len(validation_df):,}"
        )

        X_train = train_df[
            FEATURE_COLUMNS
        ].copy()

        y_train = train_df[
            TARGET_COLUMN
        ].to_numpy()

        X_validation = validation_df[
            FEATURE_COLUMNS
        ].copy()

        y_validation = validation_df[
            TARGET_COLUMN
        ].to_numpy()

        X_train["is_weekend"] = (
            X_train["is_weekend"]
            .astype("int8")
        )

        X_validation["is_weekend"] = (
            X_validation["is_weekend"]
            .astype("int8")
        )

        model = HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.1,
            max_iter=100,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=42,
        )

        print(
            "\nTraining HistGradientBoosting V3..."
        )

        start = perf_counter()

        model.fit(
            X_train,
            y_train,
        )

        elapsed = (
            perf_counter() - start
        )

        print(
            f"Training completed in "
            f"{elapsed:.2f} seconds"
        )

        predictions = model.predict(
            X_validation
        )

        predictions = np.clip(
            predictions,
            a_min=0,
            a_max=None,
        )

        v3_metrics = evaluate(
            y_validation,
            predictions,
        )

        print_metrics(
            "HISTGRADIENTBOOSTING V3 VALIDATION",
            v3_metrics,
        )

        rolling_predictions = (
            validation_df[
                "sales_rolling_mean_7"
            ].to_numpy()
        )

        rolling_metrics = evaluate(
            y_validation,
            rolling_predictions,
        )

        print_metrics(
            "7-DAY ROLLING BASELINE VALIDATION",
            rolling_metrics,
        )

        print_demand_band_diagnostics(
            actual=y_validation,
            v3_predictions=predictions,
            rolling_predictions=rolling_predictions,
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()