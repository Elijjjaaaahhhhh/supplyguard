import os
from time import perf_counter

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from sklearn.ensemble import HistGradientBoostingRegressor
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()


TARGET_COLUMN = "target_sale_amount"


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

    "discount",
    "activity_flag",
]


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


def load_dataset(
    engine,
    query: str,
) -> pd.DataFrame:
    """
    Load model-ready data from PostgreSQL.
    """
    return pd.read_sql(
        query,
        engine,
        parse_dates=["dt"],
    )


def mae(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    return np.mean(
        np.abs(actual - predicted)
    )


def rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    return np.sqrt(
        np.mean(
            np.square(actual - predicted)
        )
    )


def wape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
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


def prepare_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare model features.
    """
    X = df[
        FEATURE_COLUMNS
    ].copy()

    X["is_weekend"] = (
        X["is_weekend"]
        .astype("int8")
    )

    return X


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


def print_demand_diagnostics(
    predictions_df: pd.DataFrame,
) -> None:
    """
    Compare final model and rolling baseline by actual demand band.
    """
    diagnostics = predictions_df.copy()

    diagnostics["model_absolute_error"] = (
        diagnostics["prediction"]
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
            model_mae=(
                "model_absolute_error",
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
        "\n--- FINAL ERROR BY DEMAND BAND ---"
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
        columns = [
            "store_id",
            "product_id",
            "dt",
            TARGET_COLUMN,
            *FEATURE_COLUMNS,
        ]

        column_sql = ", ".join(
            dict.fromkeys(columns)
        )

        train_query = f"""
            SELECT
                {column_sql}
            FROM feature.v_demand_model_v3
            WHERE dt <= DATE '2024-06-25'
              AND history_count_28 = 28
            ORDER BY
                store_id,
                product_id,
                dt
        """

        eval_query = f"""
            SELECT
                {column_sql}
            FROM feature.v_demand_model_v3
            WHERE dt >= DATE '2024-06-26'
              AND dt <= DATE '2024-07-02'
              AND history_count_28 = 28
            ORDER BY
                store_id,
                product_id,
                dt
        """

        print(
            "\nLoading final training data..."
        )

        train_df = load_dataset(
            engine,
            train_query,
        )

        print(
            f"Training rows: "
            f"{len(train_df):,}"
        )

        print(
            "Training date range: "
            f"{train_df['dt'].min().date()} "
            "to "
            f"{train_df['dt'].max().date()}"
        )

        print(
            "\nLoading final evaluation data..."
        )

        eval_df = load_dataset(
            engine,
            eval_query,
        )

        print(
            f"Evaluation rows: "
            f"{len(eval_df):,}"
        )

        print(
            "Evaluation date range: "
            f"{eval_df['dt'].min().date()} "
            "to "
            f"{eval_df['dt'].max().date()}"
        )

        X_train = prepare_features(
            train_df
        )

        y_train = train_df[
            TARGET_COLUMN
        ].to_numpy()

        X_eval = prepare_features(
            eval_df
        )

        y_eval = eval_df[
            TARGET_COLUMN
        ].to_numpy()

        model = HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.1,
            max_iter=100,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=42,
        )

        print(
            "\nTraining frozen V3C model..."
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
            X_eval
        )

        predictions = np.clip(
            predictions,
            a_min=0,
            a_max=None,
        )

        model_metrics = evaluate(
            actual=y_eval,
            predicted=predictions,
        )

        rolling_predictions = (
            eval_df[
                "sales_rolling_mean_7"
            ].to_numpy()
        )

        rolling_metrics = evaluate(
            actual=y_eval,
            predicted=rolling_predictions,
        )

        print_metrics(
            "FINAL V3C EVALUATION",
            model_metrics,
        )

        print_metrics(
            "FINAL 7-DAY ROLLING BASELINE",
            rolling_metrics,
        )

        predictions_df = pd.DataFrame(
            {
                "store_id": eval_df[
                    "store_id"
                ],
                "product_id": eval_df[
                    "product_id"
                ],
                "dt": eval_df[
                    "dt"
                ],
                "actual": y_eval,
                "prediction": predictions,
                "rolling_prediction": (
                    rolling_predictions
                ),
            }
        )

        print_demand_diagnostics(
            predictions_df
        )

        output_path = (
            "outputs/"
            "final_v3c_predictions.csv"
        )

        predictions_df.to_csv(
            output_path,
            index=False,
        )

        print(
            "\nPredictions saved to:"
        )

        print(
            output_path
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()