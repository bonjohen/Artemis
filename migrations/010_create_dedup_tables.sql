-- Deduplication tables for grouping near-duplicate images.
-- Master image per group is retained; others are suppressed.

CREATE SEQUENCE IF NOT EXISTS seq_dedup_group START 1;

CREATE TABLE IF NOT EXISTS dedup_image_group (
    group_id            TEXT PRIMARY KEY,
    master_image_sk     BIGINT NOT NULL,
    member_count        INTEGER NOT NULL,
    similarity_threshold DOUBLE NOT NULL,
    dedup_run_id        TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dedup_image_member (
    group_id            TEXT NOT NULL,
    image_sk            BIGINT NOT NULL,
    similarity_to_master DOUBLE NOT NULL,
    is_master           BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (group_id, image_sk)
);

-- Suppression flag on dim_image (false = active, true = suppressed by dedup)
ALTER TABLE dim_image ADD COLUMN IF NOT EXISTS is_suppressed BOOLEAN DEFAULT false;
