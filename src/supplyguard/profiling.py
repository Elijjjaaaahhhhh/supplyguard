from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/external/eval.parquet")


def load_data(path: Path) -> pd.DataFrame:
    """
    Load a Parquet file into a pandas DataFrame.

    Parameters
    ----------
    path : Path
        Path to the Parquet file.

    Returns
    -------
    pd.DataFrame
        Loaded dataset.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    df = pd.read_parquet(path)

    return df


def basic_profile(df: pd.DataFrame) -> None:
    """
    Print basic structural information about the dataset.
    """
    print("\n--- DATASET SHAPE ---")
    print(f"Rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]}")

    print("\n--- COLUMN NAMES ---")
    print(df.columns.tolist())

    print("\n--- DATA TYPES ---")
    print(df.dtypes)

    print("\n--- MEMORY USAGE ---")
    memory_mb = df.memory_usage(deep=True).sum() / (1024**2)
    print(f"Memory usage: {memory_mb:.2f} MB")


def completeness_profile(df: pd.DataFrame) -> None:
    """
    Show missing-value counts and percentages for each column.
    """
    null_count = df.isna().sum()

    null_percentage = (
        null_count
        .div(len(df))
        .mul(100)
        .round(2)
    )

    completeness = pd.DataFrame(
        {
            "null_count": null_count,
            "null_percentage": null_percentage,
        }
    )

    print("\n--- MISSING VALUES ---")
    print(completeness)


def uniqueness_profile(df: pd.DataFrame) -> None:
    """
    Show cardinality for key business dimensions.
    """
    columns_to_check = [
        "city_id",
        "store_id",
        "product_id",
        "dt",
        "first_category_id",
        "second_category_id",
        "third_category_id",
    ]

    print("\n--- UNIQUE VALUES ---")

    for column in columns_to_check:
        unique_count = df[column].nunique(dropna=False)
        print(f"{column}: {unique_count:,}")


def integrity_profile(df: pd.DataFrame) -> None:
    """
    Check basic integrity rules and potential duplicate records.

    Exact duplicate checking excludes nested array columns because NumPy
    arrays are unhashable and cannot be used directly by DataFrame.duplicated().
    """
    nested_columns = [
        "hours_sale",
        "hours_stock_status",
    ]

    comparable_columns = [
        column
        for column in df.columns
        if column not in nested_columns
    ]

    exact_duplicates = df.duplicated(
        subset=comparable_columns
    ).sum()

    business_key = [
        "store_id",
        "product_id",
        "dt",
    ]

    duplicate_business_keys = df.duplicated(
        subset=business_key,
        keep=False,
    ).sum()

    negative_sales = (df["sale_amount"] < 0).sum()

    print("\n--- INTEGRITY CHECKS ---")
    print(
        "Exact duplicate rows "
        "(excluding nested hourly arrays): "
        f"{exact_duplicates:,}"
    )
    print(
        "Rows involved in duplicate store-product-date keys: "
        f"{duplicate_business_keys:,}"
    )
    print(f"Rows with negative sale_amount: {negative_sales:,}")


def time_profile(df: pd.DataFrame) -> None:
    """
    Convert the date column and report dataset time coverage.
    """
    dates = pd.to_datetime(
        df["dt"],
        errors="coerce",
    )

    invalid_dates = dates.isna().sum()

    print("\n--- TIME COVERAGE ---")
    print(f"Invalid dates: {invalid_dates:,}")
    print(f"Minimum date: {dates.min()}")
    print(f"Maximum date: {dates.max()}")

    if invalid_dates == 0:
        total_days = (dates.max() - dates.min()).days + 1
        print(f"Calendar span: {total_days:,} days")


def sales_profile(df: pd.DataFrame) -> None:
    """
    Perform basic checks on the sales column.
    """
    zero_sales = (df["sale_amount"] == 0).sum()
    positive_sales = (df["sale_amount"] > 0).sum()

    zero_sales_percentage = (
        zero_sales / len(df) * 100
    )

    print("\n--- SALES PROFILE ---")
    print(f"Zero-sales rows: {zero_sales:,}")
    print(
        f"Zero-sales percentage: "
        f"{zero_sales_percentage:.2f}%"
    )
    print(f"Positive-sales rows: {positive_sales:,}")

    print("\nSale amount summary:")
    print(df["sale_amount"].describe())


def hourly_structure_profile(df: pd.DataFrame) -> None:
    """
    Inspect the structure of the hourly list columns.
    """
    hours_sale_lengths = df["hours_sale"].apply(len)
    stock_status_lengths = df["hours_stock_status"].apply(len)

    print("\n--- HOURLY STRUCTURE ---")

    print("hours_sale lengths:")
    print(hours_sale_lengths.value_counts().sort_index())

    print("\nhours_stock_status lengths:")
    print(stock_status_lengths.value_counts().sort_index())


def validate_hourly_sales(df: pd.DataFrame) -> None:
    """
    Check whether daily sale_amount agrees with the sum of hourly sales.
    """
    hourly_totals = df["hours_sale"].apply(sum)

    differences = (
        df["sale_amount"] - hourly_totals
    ).abs()

    tolerance = 1e-6

    mismatches = differences > tolerance

    mismatch_count = mismatches.sum()
    mismatch_percentage = (
        mismatch_count / len(df) * 100
    )

    print("\n--- HOURLY SALES CONSISTENCY ---")
    print(
        "Rows where sale_amount differs from "
        f"sum(hours_sale): {mismatch_count:,}"
    )
    print(
        f"Mismatch percentage: "
        f"{mismatch_percentage:.2f}%"
    )

    if mismatch_count > 0:
        print("\nLargest differences:")
        print(
            differences[mismatches]
            .sort_values(ascending=False)
            .head(10)
        )



def main() -> None:
    """
    Run the initial SupplyGuard data profiling workflow.
    """
    df = load_data(DATA_PATH)

    basic_profile(df)
    completeness_profile(df)
    uniqueness_profile(df)
    integrity_profile(df)
    time_profile(df)
    sales_profile(df)
    hourly_structure_profile(df)
    validate_hourly_sales(df)

if __name__ == "__main__":
    main()