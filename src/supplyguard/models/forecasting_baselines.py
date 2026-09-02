import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()


def get_engine():
    """
    Create a SQLAlchemy connection engine for PostgreSQL.
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


def load_evaluation_data(engine) -> pd.DataFrame:
    """
    Load the model-ready evaluation period.

    Only columns required for baseline forecasting are loaded.
    """
    query = """
        SELECT
            store_id,
            product_id,
            dt,
            target_sale_amount,
            sales_lag_1,
            sales_lag_7,
            sales_rolling_mean_7
        FROM feature.v_demand_model_eval
        ORDER BY
            store_id,
            product_id,
            dt
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
    """
    Mean Absolute Error.

    Average absolute difference between actual and predicted demand.
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

    Similar to MAE, but penalises large forecasting errors more heavily.
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

    Total absolute forecasting error divided by total actual demand.
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


def evaluate_forecast(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict:
    """
    Calculate all baseline forecasting metrics.
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


def evaluate_baselines(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Evaluate simple demand forecasting baselines.
    """
    actual = df[
        "target_sale_amount"
    ].to_numpy()

    baselines = {
        "lag_1": df[
            "sales_lag_1"
        ].to_numpy(),

        "lag_7": df[
            "sales_lag_7"
        ].to_numpy(),

        "rolling_mean_7": df[
            "sales_rolling_mean_7"
        ].to_numpy(),
    }

    results = []

    for model_name, prediction in baselines.items():

        metrics = evaluate_forecast(
            actual=actual,
            predicted=prediction,
        )

        results.append(
            {
                "model": model_name,
                **metrics,
            }
        )

    results_df = pd.DataFrame(
        results
    )

    return results_df.sort_values(
        by="MAE"
    ).reset_index(drop=True)


def main() -> None:
    engine = get_engine()

    try:
        eval_df = load_evaluation_data(
            engine
        )

        print("\n--- EVALUATION DATA ---")
        print(
            f"Rows: {len(eval_df):,}"
        )

        print(
            "Date range: "
            f"{eval_df['dt'].min().date()} "
            "to "
            f"{eval_df['dt'].max().date()}"
        )

        print(
            "Store-product series: "
            f"{eval_df[['store_id', 'product_id']].drop_duplicates().shape[0]:,}"
        )

        results = evaluate_baselines(
            eval_df
        )

        print(
            "\n--- FORECASTING BASELINES ---"
        )

        print(
            results.to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}",
            )
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()