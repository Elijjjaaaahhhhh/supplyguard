CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.pipeline_run (
    run_id UUID PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    as_of_date DATE,
    config JSONB NOT NULL,
    code_revision TEXT,
    model_id TEXT,
    summary JSONB,
    error TEXT
);
CREATE TABLE IF NOT EXISTS ops.pipeline_stage (
    run_id UUID NOT NULL REFERENCES ops.pipeline_run,
    stage TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    details JSONB,
    PRIMARY KEY (run_id, stage)
);
CREATE TABLE IF NOT EXISTS ops.source_file (
    name TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    row_count BIGINT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ops.model_artifact (
    model_id TEXT PRIMARY KEY,
    trained_through DATE NOT NULL,
    artifact_path TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    manifest JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ops.forecast (
    run_id UUID NOT NULL REFERENCES ops.pipeline_run,
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    as_of_date DATE NOT NULL,
    target_date DATE NOT NULL,
    model_id TEXT NOT NULL REFERENCES ops.model_artifact,
    prediction DOUBLE PRECISION NOT NULL CHECK (prediction >= 0 AND prediction < 'Infinity'::FLOAT8),
    input_policy TEXT NOT NULL,
    PRIMARY KEY (run_id,store_id,product_id,target_date),
    CHECK (target_date = as_of_date + 1)
);
CREATE INDEX IF NOT EXISTS forecast_cutoff_idx ON ops.forecast(as_of_date,target_date);
