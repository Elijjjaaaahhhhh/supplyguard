import logging

from supplyguard.database import get_connection
from supplyguard.logging_config import configure_logging


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Raised when a SupplyGuard data-quality validation fails.
    """


def run_scalar_check(
    cursor,
    check_name: str,
    query: str,
    expected_value,
) -> None:
    """
    Run a SQL query expected to return one scalar value
    and compare it with the expected result.
    """
    cursor.execute(query)

    actual_value = cursor.fetchone()[0]

    if actual_value != expected_value:
        raise ValidationError(
            f"{check_name} failed: "
            f"expected {expected_value}, "
            f"got {actual_value}"
        )

    logger.info(
        "PASS | %s | value=%s",
        check_name,
        actual_value,
    )


def validate_pipeline() -> None:
    """
    Run core SupplyGuard data-quality validations.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:

            run_scalar_check(
                cursor=cursor,
                check_name="raw row count",
                query="""
                    SELECT COUNT(*)
                    FROM raw.retail_daily
                """,
                expected_value=4_850_000,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="staging row count",
                query="""
                    SELECT COUNT(*)
                    FROM staging.retail_daily
                """,
                expected_value=4_850_000,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="core fact row count",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand
                """,
                expected_value=4_850_000,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="product dimension count",
                query="""
                    SELECT COUNT(*)
                    FROM core.dim_product
                """,
                expected_value=865,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="store dimension count",
                query="""
                    SELECT COUNT(*)
                    FROM core.dim_store
                """,
                expected_value=898,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="date dimension count",
                query="""
                    SELECT COUNT(*)
                    FROM core.dim_date
                """,
                expected_value=97,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="staging duplicate business keys",
                query="""
                    SELECT COUNT(*)
                    FROM (
                        SELECT
                            store_id,
                            product_id,
                            dt
                        FROM staging.retail_daily
                        GROUP BY
                            store_id,
                            product_id,
                            dt
                        HAVING COUNT(*) > 1
                    ) AS duplicates
                """,
                expected_value=0,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="negative core sales",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand
                    WHERE sale_amount < 0
                """,
                expected_value=0,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="invalid core stockout hours",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand
                    WHERE stockout_hours NOT BETWEEN 0 AND 16
                """,
                expected_value=0,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="orphan product foreign keys",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand AS f
                    LEFT JOIN core.dim_product AS p
                        ON f.product_id = p.product_id
                    WHERE p.product_id IS NULL
                """,
                expected_value=0,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="orphan store foreign keys",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand AS f
                    LEFT JOIN core.dim_store AS s
                        ON f.store_id = s.store_id
                    WHERE s.store_id IS NULL
                """,
                expected_value=0,
            )

            run_scalar_check(
                cursor=cursor,
                check_name="orphan date foreign keys",
                query="""
                    SELECT COUNT(*)
                    FROM core.fact_daily_demand AS f
                    LEFT JOIN core.dim_date AS d
                        ON f.dt = d.dt
                    WHERE d.dt IS NULL
                """,
                expected_value=0,
            )

    logger.info("All SupplyGuard validations passed.")


def main() -> None:
    configure_logging()
    validate_pipeline()


if __name__ == "__main__":
    main()