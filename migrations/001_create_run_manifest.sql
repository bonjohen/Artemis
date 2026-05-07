-- Pipeline audit trail: one row per collection or processing action
CREATE TABLE IF NOT EXISTS run_manifest (
    run_id              TEXT PRIMARY KEY,
    pipeline_name       TEXT NOT NULL,
    dataset_name        TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    source_url          TEXT,
    downloaded_at       TIMESTAMPTZ,
    raw_checksum        TEXT,
    raw_file_path       TEXT,
    row_count_raw       INTEGER,
    row_count_loaded    INTEGER,
    load_status         TEXT,
    skip_reason         TEXT,
    failure_message     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);
