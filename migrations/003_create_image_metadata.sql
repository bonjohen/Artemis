-- Staging tables for parsed source data
CREATE TABLE IF NOT EXISTS stg_timeline_photo (
    load_run_id     TEXT NOT NULL,
    file_name       TEXT,
    title           TEXT,
    description     TEXT,
    photographer    TEXT,
    location        TEXT,
    camera          TEXT,
    settings        TEXT,
    time_str        TEXT,
    spacecraft      BOOLEAN,
    batch           INTEGER,
    enabled         BOOLEAN,
    camera_id       TEXT,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg_vote_manifest_image (
    load_run_id     TEXT NOT NULL,
    guid            TEXT NOT NULL,
    nasa_link       TEXT,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg_category (
    load_run_id     TEXT NOT NULL,
    category_key    TEXT NOT NULL,
    category_slug   TEXT,
    category_label  TEXT,
    image_count     INTEGER,
    showcase_guid   TEXT,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg_leaderboard_batch (
    load_run_id     TEXT NOT NULL,
    guid            TEXT NOT NULL,
    picks           INTEGER,
    shown           INTEGER,
    rate            DOUBLE,
    wilson          DOUBLE,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg_leaderboard_elo (
    load_run_id     TEXT NOT NULL,
    guid            TEXT NOT NULL,
    elo             DOUBLE,
    wins            INTEGER,
    losses          INTEGER,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg_vote_counts (
    load_run_id     TEXT NOT NULL,
    ballot_count    INTEGER,
    unique_picked   INTEGER,
    loaded_at       TIMESTAMPTZ DEFAULT now()
);

-- Warehouse dimension tables
CREATE SEQUENCE IF NOT EXISTS seq_image_sk START 1;

CREATE TABLE IF NOT EXISTS dim_image (
    image_sk            BIGINT PRIMARY KEY DEFAULT nextval('seq_image_sk'),
    source_image_id     TEXT NOT NULL UNIQUE,
    source_file_name    TEXT,
    media_type          TEXT DEFAULT 'photo',
    title               TEXT,
    description         TEXT,
    photographer        TEXT,
    location            TEXT,
    camera              TEXT,
    settings            TEXT,
    taken_at_str        TEXT,
    spacecraft_flag     BOOLEAN,
    enabled_flag        BOOLEAN,
    timeline_flag       BOOLEAN DEFAULT false,
    vote_pool_flag      BOOLEAN DEFAULT false,
    thumb_downloaded    BOOLEAN DEFAULT false,
    full_downloaded     BOOLEAN DEFAULT false,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS seq_category_sk START 1;

CREATE TABLE IF NOT EXISTS dim_category (
    category_sk         BIGINT PRIMARY KEY DEFAULT nextval('seq_category_sk'),
    category_key        TEXT NOT NULL UNIQUE,
    category_slug       TEXT,
    category_label      TEXT,
    image_count         INTEGER,
    created_at          TIMESTAMPTZ DEFAULT now()
);
