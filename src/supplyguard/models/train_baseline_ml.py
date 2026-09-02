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
    "sales_lag_7",
    "sales_lag_14",
    "sales_rolling_mean_7",
    "sales_rolling_mean_14",
    "sales_rolling_std_7",
    "stockout_lag_1",
    "stockout_rolling_mean_7",
]

TARGET_COLUMN = "target_sale_amount"


def get_engine():
    """
    Create the PostgreSQL SQLAlchemy engine.
    """
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
    """
    Load a model-ready feature view from PostgreSQL.
    """
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


def mae(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """
    Mean Absolute Error.
    """
    return np.mean(
        np.abs(actual - predicted)
    )


def rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """
    Root Mean Squared Error.
    """
    return np.sqrt(
        np.mean(
            np.square(actual - predicted)
        )
    )


def wape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    """
    Weighted Absolute Percentage Error.
    """
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


def evaluate(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict:
    """
    Calculate forecasting metrics.
    """
    return {
        "MAE": mae(
            actual,
            predicted,
        ),
        "RMSE": rmse(
            actual,
            predicted,
        ),
        "WAPE": wape(
            actual,
            predicted,
        ),
    }


def build_error_diagnostics(
    validation_df: pd.DataFrame,
    actual: np.ndarray,
    ml_predictions: np.ndarray,
    baseline_predictions: np.ndarray,
) -> pd.DataFrame:
    """
    Build row-level forecasting error information.

    Positive signed error:
        prediction > actual
        overforecast

    Negative signed error:
        prediction < actual
        underforecast
    """
    diagnostics = validation_df[
        [
            "store_id",
            "product_id",
            "target_sale_amount",
            "is_weekend",
            "stockout_lag_1",
            "stockout_rolling_mean_7",
        ]
    ].copy()

    diagnostics["actual"] = actual

    diagnostics["ml_prediction"] = (
        ml_predictions
    )

    diagnostics["baseline_prediction"] = (
        baseline_predictions
    )

    diagnostics["ml_signed_error"] = (
        diagnostics["ml_prediction"]
        - diagnostics["actual"]
    )

    diagnostics["baseline_signed_error"] = (
        diagnostics["baseline_prediction"]
        - diagnostics["actual"]
    )

    diagnostics["ml_absolute_error"] = (
        diagnostics["ml_signed_error"].abs()
    )

    diagnostics["baseline_absolute_error"] = (
        diagnostics["baseline_signed_error"].abs()
    )

    return diagnostics


def print_direction_diagnostics(
    diagnostics: pd.DataFrame,
) -> None:
    """
    Compare underforecast, overforecast and exact-forecast rates.
    """
    print(
        "\n--- FORECAST DIRECTION ---"
    )

    for model_name in [
        "ml",
        "baseline",
    ]:
        error_column = (
            f"{model_name}_signed_error"
        )

        underforecast_rate = (
            diagnostics[error_column] < 0
        ).mean()

        overforecast_rate = (
            diagnostics[error_column] > 0
        ).mean()

        exact_rate = (
            diagnostics[error_column] == 0
        ).mean()

        print(
            f"\n{model_name.upper()}"
        )

        print(
            "Underforecast rate: "
            f"{underforecast_rate:.2%}"
        )

        print(
            "Overforecast rate: "
            f"{overforecast_rate:.2%}"
        )

        print(
            "Exact forecast rate: "
            f"{exact_rate:.2%}"
        )


def print_weekend_diagnostics(
    diagnostics: pd.DataFrame,
) -> None:
    """
    Compare model errors on weekdays and weekends.
    """
    summary = (
        diagnostics
        .groupby("is_weekend")
        .agg(
            observations=(
                "actual",
                "size",
            ),
            actual_mean=(
                "actual",
                "mean",
            ),
            ml_mae=(
                "ml_absolute_error",
                "mean",
            ),
            baseline_mae=(
                "baseline_absolute_error",
                "mean",
            ),
        )
        .reset_index()
    )

    print(
        "\n--- WEEKDAY VS WEEKEND ERROR ---"
    )

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )


def print_demand_band_diagnostics(
    diagnostics: pd.DataFrame,
) -> None:
    """
    Compare forecasting errors across actual demand levels.
    """
    diagnostics = diagnostics.copy()

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
            ml_mae=(
                "ml_absolute_error",
                "mean",
            ),
            baseline_mae=(
                "baseline_absolute_error",
                "mean",
            ),
        )
        .reset_index()
    )

    print(
        "\n--- ERROR BY ACTUAL DEMAND ---"
    )

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )


def print_stockout_diagnostics(
    diagnostics: pd.DataFrame,
) -> None:
    """
    Compare forecasting errors based on recent stockout exposure.
    """
    diagnostics = diagnostics.copy()

    diagnostics["stockout_band"] = pd.cut(
        diagnostics[
            "stockout_rolling_mean_7"
        ],
        bins=[
            -np.inf,
            0,
            4,
            8,
            np.inf,
        ],
        labels=[
            "No recent stockout",
            "0-4 hours",
            "4-8 hours",
            ">8 hours",
        ],
    )

    summary = (
        diagnostics
        .groupby(
            "stockout_band",
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
            ml_mae=(
                "ml_absolute_error",
                "mean",
            ),
            baseline_mae=(
                "baseline_absolute_error",
                "mean",
            ),
        )
        .reset_index()
    )

    print(
        "\n--- ERROR BY RECENT STOCKOUT EXPOSURE ---"
    )

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )


def main() -> None:
    """
    Train the baseline machine-learning model,
    compare it with the rolling baseline,
    and analyse where forecasting errors occur.
    """
    engine = get_engine()

    try:
        print(
            "\nLoading development training data..."
        )

        train_df = load_dataset(
            engine,
            "feature.v_demand_model_dev_train",
        )

        print(
            f"Training rows: {len(train_df):,}"
        )

        print(
            "\nLoading validation data..."
        )

        validation_df = load_dataset(
            engine,
            "feature.v_demand_model_validation",
        )

        print(
            f"Validation rows: "
            f"{len(validation_df):,}"
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

        # Boolean values are explicitly converted
        # into numeric 0/1 values for the model.
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
            "\nTraining HistGradientBoosting model..."
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

        # Negative demand is not operationally meaningful.
        predictions = np.clip(
            predictions,
            a_min=0,
            a_max=None,
        )

        metrics = evaluate(
            actual=y_validation,
            predicted=predictions,
        )

        print(
            "\n--- HISTGRADIENTBOOSTING VALIDATION ---"
        )

        for metric, value in metrics.items():
            print(
                f"{metric}: {value:.4f}"
            )

        # Our strongest simple forecasting baseline.
        rolling_predictions = (
            validation_df[
                "sales_rolling_mean_7"
            ].to_numpy()
        )

        baseline_metrics = evaluate(
            actual=y_validation,
            predicted=rolling_predictions,
        )

        print(
            "\n--- 7-DAY ROLLING BASELINE VALIDATION ---"
        )

        for metric, value in baseline_metrics.items():
            print(
                f"{metric}: {value:.4f}"
            )


        diagnostics = build_error_diagnostics(
            validation_df=validation_df,
            actual=y_validation,
            ml_predictions=predictions,
            baseline_predictions=rolling_predictions,
        )

        print_direction_diagnostics(
            diagnostics
        )

        print_weekend_diagnostics(
            diagnostics
        )

        print_demand_band_diagnostics(
            diagnostics
        )

        print_stockout_diagnostics(
            diagnostics
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()