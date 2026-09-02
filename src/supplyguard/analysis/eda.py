from pathlib import Path
import os

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()

FIGURE_DIR = Path("outputs/figures")
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def get_engine():
    """
    Create a SQLAlchemy engine using SupplyGuard environment variables.
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


def load_daily_network_metrics(engine) -> pd.DataFrame:
    """
    Load network-level daily demand and stockout metrics.
    """
    query = """
        SELECT
            dt,
            SUM(sale_amount) AS total_sales,
            AVG(sale_amount) AS average_sales,
            AVG(stockout_hours) AS average_stockout_hours
        FROM core.fact_daily_demand
        WHERE source_file = 'train.parquet'
        GROUP BY dt
        ORDER BY dt
    """

    return pd.read_sql(
        query,
        engine,
        parse_dates=["dt"],
    )


def plot_daily_sales(df: pd.DataFrame) -> None:
    """
    Plot total network sales through time.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        df["dt"],
        df["total_sales"],
    )

    ax.set_title(
        "SupplyGuard — Daily Observed Sales"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Total observed sales")

    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = (
        FIGURE_DIR / "daily_observed_sales.png"
    )

    fig.savefig(
        output_path,
        dpi=150,
    )

    plt.close(fig)


def plot_sales_with_rolling_average(
    df: pd.DataFrame,
) -> None:
    """
    Plot daily sales with a 7-day rolling average.
    """
    plot_df = df.copy()

    plot_df["rolling_sales_7d"] = (
        plot_df["total_sales"]
        .rolling(window=7)
        .mean()
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        plot_df["dt"],
        plot_df["total_sales"],
        label="Daily sales",
    )

    ax.plot(
        plot_df["dt"],
        plot_df["rolling_sales_7d"],
        label="7-day rolling average",
    )

    ax.set_title(
        "SupplyGuard — Daily Sales and 7-Day Trend"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Total observed sales")

    ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = (
        FIGURE_DIR / "daily_sales_7d_rolling.png"
    )

    fig.savefig(
        output_path,
        dpi=150,
    )

    plt.close(fig)


def plot_stockout_trend(
    df: pd.DataFrame,
) -> None:
    """
    Plot average daily stockout exposure.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        df["dt"],
        df["average_stockout_hours"],
    )

    ax.set_title(
        "SupplyGuard — Average Stockout Exposure"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(
        "Average out-of-stock hours"
    )

    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = (
        FIGURE_DIR / "daily_stockout_exposure.png"
    )

    fig.savefig(
        output_path,
        dpi=150,
    )

    plt.close(fig)


def main() -> None:
    engine = get_engine()

    daily_metrics = load_daily_network_metrics(
        engine
    )

    print(daily_metrics.head())
    print()
    print(daily_metrics.dtypes)

    plot_daily_sales(daily_metrics)

    plot_sales_with_rolling_average(
        daily_metrics
    )

    plot_stockout_trend(
        daily_metrics
    )

    engine.dispose()

    print(
        "\nEDA figures created in "
        "outputs/figures/"
    )


if __name__ == "__main__":
    main()