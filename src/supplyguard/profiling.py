from pathlib import Path

import pandas as pd

import pyarrow.parquet as pq

TRAIN_PATH = Path("data/external/train.parquet")
EVAL_PATH = Path("data/external/eval.parquet")


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


def parquet_metadata_profile(path: Path) -> None:
    """
    Inspect Parquet metadata without loading the full dataset.
    """
    if not path.exists():
        raise FileNotFoundError(f"Data File not Found: {path}")

    parquet_file = pq.ParquetFile(path)

    metadata = parquet_file.metadata


    print("\n --- PARQUET METADATA ---")
    print(f"File: {path.name}")
    print(f"Rows: {metadata.num_rows:,}")
    print(f"Columns: {metadata.num_columns}")
    print(f"Row groups: {metadata.num_row_groups:,}")


def grain_profile(path:Path) -> None:
    """
    Validate the expected store-product-date grain.
    """
    columns = [
        "store_id", "product_id", "dt",
    ]

    df = pd.read_parquet(
        path, 
        columns=columns,
    )

    duplicate_keys = df.duplicated(
        subset=columns,
        keep=False,
    ).sum()


    unique_series = (
        df[["store_id", "product_id"]]
        .drop_duplicates()
        .shape[0]
    )


    print("\n--- GRAIN PROFILE ---")
    print(
        "Expected grain: "
        "one row per store-product-date"
    )
    print(
        f"Rows involved in duplicate business keys: "
        f"{duplicate_keys:,}"
    )
    print(
        f"Unique store-product series: "
        f"{unique_series:,}"
    )


def efficient_time_profile(path:Path) -> None:
    """
    Profile date coverage using only the date column.
    """

    df = pd.read_parquet(
        path,
        columns=["dt"],
    )

    dates = pd.to_datetime(
        df["dt"],
        errors="coerce",
    )

    invalid_dates = dates.isna().sum()

    print("\n--- TIME PROFILE ---")
    print(f"Invalid dates: {invalid_dates:,}")
    print(f"Unique dates: {dates.nunique():,}")
    print(f"Minimum date: {dates.min()}")
    print(f"Maximum date: {dates.max()}")


    if invalid_dates == 0:
        calendar_span = (
            dates.max() - dates.min()
        ).days+1

        print(
            f"Calendar span: "
            f"{calendar_span:,} days"
        )

def efficient_sales_profile(path:Path) -> None:
    """
    Profile daily sales without loading unrelated columns.
    """
    df = pd.read_parquet(
        path,
        columns=["sale_amount"],
    )

    zero_sales = (df["sale_amount"] == 0).sum()
    negative_sales = (df["sale_amount"] < 0 ).sum()

    print("\n--- SALES PROFILE ---")
    print(f"Zero-sales rows: {zero_sales:,}")
    print(
        "Zero-sales percentage: "
        f"{zero_sales / len(df) * 100:.2f}%"
    )
    print(
        f"Negative-sales rows: "
        f"{negative_sales:,}"
    )

    print("\nSale amount summary:")
    print(df["sale_amount"].describe())

def category_consistency_profile(path: Path) -> None:
    """
    Check whether each product maps consistently to one category hierarchy.
    """

    columns = [
        "product_id",
        "first_category_id",
        "second_category_id",
        "third_category_id",
    ]

    df= pd.read_parquet(
        path,
        columns=columns,
    )

    product_category_counts = (
        df.drop_duplicates()
        .groupby("product_id")
        .size()
    )

    inconsistent_products = (
        product_category_counts > 1
    ).sum()

    print("\n--- CATEGORY CONSISTENCY ---")
    print(
        "Products mapped to multiple "
        "category combinations: "
        f"{inconsistent_products:,}"
    )


def compare_train_eval_population(
        train_path: Path,
        eval_path: Path,
) -> None:
    """
    Compare store-product populations between training and evaluation data.
    """
    columns =[
        "store_id",
        "product_id",
    ]

    train = (
        pd.read_parquet(
            train_path,
            columns=columns,
        )
        .drop_duplicates()
    )

    eval_df = (
            pd.read_parquet(
                eval_path,
                columns=columns,
            )
            .drop_duplicates()
        )

    merged = train.merge(
        eval_df,
        on=columns,
        how="outer",
        indicator=True,
    )

    counts = merged["_merge"].value_counts()

    print("\n--- TRAIN / EVAL POPULATION ---")
    print(counts)

    only_train = (
        merged["_merge"] == "left_only"
    ).sum()

    only_eval = (
        merged["_merge"] == "right_only"
    ).sum()

    print(
        f"Series only in training: "
        f"{only_train:,}"
    )
    print(
        f"Series only in evaluation: "
        f"{only_eval:,}"
    )

def scalable_training_profile() -> None:
    """
    Run memory-conscious profiling on the full training dataset.
    """

    parquet_metadata_profile (TRAIN_PATH)
    grain_profile (TRAIN_PATH)
    efficient_time_profile (TRAIN_PATH)
    efficient_sales_profile (TRAIN_PATH)
    category_consistency_profile (TRAIN_PATH)
    stock_status_structure_profile(TRAIN_PATH)
    validate_stock_count_relationship(TRAIN_PATH)
    stockout_sales_profile(TRAIN_PATH)



    compare_train_eval_population(
        TRAIN_PATH,
        EVAL_PATH,
    )


def stock_status_structure_profile(path: Path) -> None:
    """
    Inspect the values and relationship between the daily stock-count
    field and the hourly stock-status array.
    """
    df = pd.read_parquet(
        path,
        columns= [
            "stock_hour6_22_cnt",
            "hours_stock_status",
        ],
    )

    print("\n--- STOCK STATUS STRUCTURE ---")

    hourly_status_values = set()

    for statuses in df["hours_stock_status"]:
        hourly_status_values.update(statuses)

    print(
        "Unique hourly stock-status values: "
        f"{sorted(hourly_status_values)}"
    )

    print("\nstock_hour6_22_cnt summary:")
    print(df["stock_hour6_22_cnt"].describe())

    print("\nstock_hour6_22_cnt value counts:")
    print(
        df["stock_hour6_22_cnt"]
        .value_counts()
        .sort_index()
    )

def validate_stock_count_relationship(path: Path) -> None:
    """
    Investigate how stock_hour6_22_cnt is derived from hours_stock_status.

    We test candidate interpretations rather than assuming the field's
    meaning from its name.
    """
    df = pd.read_parquet(
        path,
        columns=[
            "stock_hour6_22_cnt",
            "hours_stock_status",
        ],
    )

    # Python slicing excludes the final index.
    # [6:23] therefore selects indices 6 through 22.
    operating_hours = df["hours_stock_status"].apply(
        lambda statuses: statuses[6:22]
    )

    count_ones = operating_hours.apply(
        lambda statuses: sum(value == 1 for value in statuses)
    )

    count_zeros = operating_hours.apply(
        lambda statuses: sum(value == 0 for value in statuses)
    )

    matches_ones = (
        count_ones == df["stock_hour6_22_cnt"]
    ).sum()

    matches_zeros = (
        count_zeros == df["stock_hour6_22_cnt"]
    ).sum()

    total_rows = len(df)

    print("\n--- STOCK COUNT RELATIONSHIP ---")

    print(
        "Rows where stock_hour6_22_cnt equals "
        f"count of 1s from hours 6-22: "
        f"{matches_ones:,} "
        f"({matches_ones / total_rows * 100:.2f}%)"
    )

    print(
        "Rows where stock_hour6_22_cnt equals "
        f"count of 0s from hours 6-22: "
        f"{matches_zeros:,} "
        f"({matches_zeros / total_rows * 100:.2f}%)"
    )


def stockout_sales_profile(path: Path) -> None:
    """
    Compare observed sales across different levels of stockout exposure.

    stock_hour6_22_cnt represents the number of out-of-stock hours
    during the 06:00-22:00 operating window.
    """
    df = pd.read_parquet(
        path,
        columns=[
            "sale_amount",
            "stock_hour6_22_cnt",
        ],
    )

    # Create interpretable stockout-severity groups.
    df["stockout_band"] = pd.cut(
        df["stock_hour6_22_cnt"],
        bins=[-1, 0, 4, 8, 12, 16],
        labels=[
            "No stockout",
            "1-4 hours",
            "5-8 hours",
            "9-12 hours",
            "13-16 hours",
        ],
    )

    summary = (
        df.groupby(
            "stockout_band",
            observed=True,
        )
        .agg(
            rows=("sale_amount", "size"),
            average_sales=("sale_amount", "mean"),
            median_sales=("sale_amount", "median"),
            zero_sales_rate=(
                "sale_amount",
                lambda x: (x == 0).mean() * 100,
            ),
            average_stockout_hours=(
                "stock_hour6_22_cnt",
                "mean",
            ),
        )
        .round(3)
    )

    print("\n--- SALES BY STOCKOUT SEVERITY ---")
    print(summary)



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
    scalable_training_profile()