from supplyguard.database import get_connection


def start_pipeline_run(
    pipeline_name: str,
    source_file: str,
    expected_rows: int,
) -> int:
    """
    Record the start of a pipeline execution.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO raw.pipeline_run (
                    pipeline_name,
                    source_file,
                    status,
                    expected_rows
                )
                VALUES (%s, %s, 'running', %s)
                RETURNING run_id
                """,
                (
                    pipeline_name,
                    source_file,
                    expected_rows,
                ),
            )

            return cursor.fetchone()[0]


def complete_pipeline_run(
    run_id: int,
    loaded_rows: int,
) -> None:
    """
    Mark a pipeline run as successful.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE raw.pipeline_run
                SET
                    status = 'success',
                    loaded_rows = %s,
                    finished_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (
                    loaded_rows,
                    run_id,
                ),
            )


def fail_pipeline_run(
    run_id: int,
    error_message: str,
) -> None:
    """
    Mark a pipeline run as failed.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE raw.pipeline_run
                SET
                    status = 'failed',
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = %s
                WHERE run_id = %s
                """,
                (
                    error_message,
                    run_id,
                ),
            )