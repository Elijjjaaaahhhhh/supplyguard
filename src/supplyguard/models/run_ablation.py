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


# V2 historical feature set

HISTORICAL_FEATURES = [
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
]


# Commercial features

COMMERCIAL_FEATURES = [
    "discount",
    "activity_flag",
]


# Weather features

WEATHER_FEATURES = [
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
]


# Model experiments

EXPERIMENTS = {
    "V2_history_only": (
        HISTORICAL_FEATURES
    ),

    "V3C_history_commercial": (
        HISTORICAL_FEATURES
        + COMMERCIAL_FEATURES
    ),

    "V3W_history_weather": (
        HISTORICAL_FEATURES
        + WEATHER_FEATURES
    ),

    "V3_full": (
        HISTORICAL_FEATURES
        + COMMERCIAL_FEATURES
        + WEATHER_FEATURES
    ),
}


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
    view_name: str,
) -> pd.DataFrame:
    """
    Load all columns required by any ablation experiment.

    Data is loaded once and reused across models.
    """
    all_features = list(
        dict.fromkeys(
            HISTORICAL_FEATURES
            + COMMERCIAL_FEATURES
            + WEATHER_FEATURES
        )
    )

    columns = [
        TARGET_COLUMN,
        *all_features,
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
    return np.mean(
        np.abs(actual - predicted)
    )


def rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:
    return np.sqrt(
        np.mean(
            np.square(
                actual - predicted
            )
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
            np.abs(
                actual - predicted
            )
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
    feature_columns: list[str],
) -> pd.DataFrame:
    """
    Select and prepare features for a model experiment.
    """
    X = df[
        feature_columns
    ].copy()

    if "is_weekend" in X.columns:
        X["is_weekend"] = (
            X["is_weekend"]
            .astype("int8")
        )

    return X


def train_experiment(
    experiment_name: str,
    feature_columns: list[str],
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> dict:
    """
    Train one HistGradientBoosting ablation experiment.
    """
    print(
        f"\nTraining: {experiment_name}"
    )

    print(
        f"Features: {len(feature_columns)}"
    )

    X_train = prepare_features(
        train_df,
        feature_columns,
    )

    X_validation = prepare_features(
        validation_df,
        feature_columns,
    )

    y_train = train_df[
        TARGET_COLUMN
    ].to_numpy()

    y_validation = validation_df[
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

    start = perf_counter()

    model.fit(
        X_train,
        y_train,
    )

    elapsed = (
        perf_counter() - start
    )

    predictions = model.predict(
        X_validation
    )

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
        f"Training time: "
        f"{elapsed:.2f} seconds"
    )

    print(
        f"MAE:  {metrics['MAE']:.4f}"
    )

    print(
        f"RMSE: {metrics['RMSE']:.4f}"
    )

    print(
        f"WAPE: {metrics['WAPE']:.4f}"
    )

    return {
        "model": experiment_name,
        "features": len(feature_columns),
        "training_seconds": elapsed,
        **metrics,
    }


def main():
    engine = get_engine()

    try:
        print(
            "\nLoading ablation training data..."
        )

        train_df = load_dataset(
            engine,
            "feature.v_demand_model_v3_dev_train",
        )

        print(
            f"Training rows: "
            f"{len(train_df):,}"
        )

        print(
            "\nLoading ablation validation data..."
        )

        validation_df = load_dataset(
            engine,
            "feature.v_demand_model_v3_validation",
        )

        print(
            f"Validation rows: "
            f"{len(validation_df):,}"
        )

        results = []

        for (
            experiment_name,
            feature_columns,
        ) in EXPERIMENTS.items():

            result = train_experiment(
                experiment_name=experiment_name,
                feature_columns=feature_columns,
                train_df=train_df,
                validation_df=validation_df,
            )

            results.append(
                result
            )

        results_df = pd.DataFrame(
            results
        )

        results_df = (
            results_df
            .sort_values("MAE")
            .reset_index(drop=True)
        )

        print(
            "\n"
            "========================================"
        )

        print(
            "ABLATION RESULTS"
        )

        print(
            "========================================"
        )

        print(
            results_df.to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}",
            )
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()