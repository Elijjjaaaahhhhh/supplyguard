CREATE TABLE IF NOT EXISTS raw.pipeline_run (
    run_id BIGSERIAL PRIMARY KEY,

    pipeline_name TEXT NOT NULL,
    source_file TEXT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN ('running', 'success', 'failed')),

    expected_rows BIGINT,
    loaded_rows BIGINT,

    started_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMPTZ,

    error_message TEXT
);