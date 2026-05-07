-- Source registry: what to collect and when it last changed
CREATE TABLE IF NOT EXISTS source_manifest (
    source_name         TEXT PRIMARY KEY,
    source_type         TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    expected_format     TEXT NOT NULL,
    refresh_frequency   TEXT DEFAULT 'manual',
    active_flag         BOOLEAN DEFAULT true,
    last_checked_at     TIMESTAMPTZ,
    last_checksum       TEXT,
    last_changed_at     TIMESTAMPTZ,
    notes               TEXT
);
