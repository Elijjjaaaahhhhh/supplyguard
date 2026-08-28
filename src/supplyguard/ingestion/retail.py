from pathlib import Path
from time import perf_counter
import logging

import pyarrow.parquet as pq

from supplyguard.database import get_connection
from supplyguard.logging_config import configure_logging
from supplyguard.pipeline_runs import (
    complete_pipeline_run,
    fail_pipeline_run,
    start_pipeline_run,
)


RAW_TABLE = "raw.retail_daily"

SOURCE_COLUMNS = [
    "city_id",
    "store_id",
    "management_group_id",
    "first_category_id",
    "second_category_id",
    "third_category_id",
    "product_id",
    "dt",
    "sale_amount",
    "hours_sale",
    "stock_hour6_22_cnt",
    "hours_stock_status",
    "discount",
    "holiday_flag",
    "activity_flag",
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
]


logger = logging.getLogger(__name__)


def convert_value(value):
    """
    Convert PyArrow values into ordinary Python values
    that Psycopg can send cleanly to PostgreSQL.

    Array-like values such as hours_sale and hours_stock_status
    are converted into Python lists.
    """
    if hasattr(value, "tolist"):
        return value.tolist()

    return value


def ingest_parquet(
    path: Path,
    batch_size: int = 10_000,
) -> int:
    """
    Bulk-load a FreshRetailNet Parquet file into raw.retail_daily.

    The function:
    1. checks that the source file exists;
    2. reads Parquet metadata;
    3. records a pipeline run;
    4. prevents duplicate loading of the same source file;
    5. streams the file to PostgreSQL using COPY;
    6. records success or failure;
    7. returns the total number of rows loaded.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Source file not found: {path}"
        )

    parquet_file = pq.ParquetFile(path)

    total_rows = parquet_file.metadata.num_rows

    logger.info("Source file: %s", path.name)
    logger.info(
        "Rows expected: %s",
        f"{total_rows:,}",
    )
    logger.info(
        "Batch size: %s",
        f"{batch_size:,}",
    )

    run_id = start_pipeline_run(
        pipeline_name="retail_parquet_ingestion",
        source_file=path.name,
        expected_rows=total_rows,
    )

    copy_sql = f"""
        COPY {RAW_TABLE} (
            {", ".join(SOURCE_COLUMNS)},
            source_file
        )
        FROM STDIN
    """

    rows_loaded = 0
    start_time = perf_counter()

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # Prevent the same source file from being loaded twice.
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {RAW_TABLE}
                    WHERE source_file = %s
                    """,
                    (path.name,),
                )

                existing_rows = cursor.fetchone()[0]

                if existing_rows > 0:
                    raise RuntimeError(
                        f"{path.name} has already been loaded "
                        f"({existing_rows:,} rows found)."
                    )

                # Stream rows to PostgreSQL using COPY.
                with cursor.copy(copy_sql) as copy:

                    for batch in parquet_file.iter_batches(
                        batch_size=batch_size,
                        columns=SOURCE_COLUMNS,
                    ):
                        batch_dict = batch.to_pydict()

                        for row_index in range(batch.num_rows):

                            row = [
                                convert_value(
                                    batch_dict[column][row_index]
                                )
                                for column in SOURCE_COLUMNS
                            ]

                            # Add source lineage.
                            row.append(path.name)

                            copy.write_row(row)

                            rows_loaded += 1

                        if rows_loaded % 100_000 == 0:
                            logger.info(
                                "Loaded %s/%s rows",
                                f"{rows_loaded:,}",
                                f"{total_rows:,}",
                            )

        elapsed = perf_counter() - start_time

        complete_pipeline_run(
            run_id=run_id,
            loaded_rows=rows_loaded,
        )

        logger.info("Ingestion complete.")
        logger.info(
            "Rows loaded: %s",
            f"{rows_loaded:,}",
        )
        logger.info(
            "Elapsed time: %.2f seconds",
            elapsed,
        )

        return rows_loaded

    except Exception as exc:
        fail_pipeline_run(
            run_id=run_id,
            error_message=str(exc),
        )

        logger.exception(
            "Ingestion failed for %s",
            path.name,
        )

        raise


def main() -> None:
    """
    Run the ingestion pipeline.

    We currently point this at eval.parquet so we can test
    the new pipeline-run metadata using an already-loaded file.
    """
    configure_logging()

    eval_path = Path(
        "data/external/eval.parquet"
    )

    ingest_parquet(eval_path)


if __name__ == "__main__":
    main()