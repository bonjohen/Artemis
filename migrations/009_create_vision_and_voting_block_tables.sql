-- Vision attribute vocabulary dimension
CREATE TABLE IF NOT EXISTS dim_image_attribute (
    attribute_code   TEXT PRIMARY KEY,
    attribute_label  TEXT NOT NULL,
    attribute_description TEXT,
    attribute_type   TEXT NOT NULL,
    is_derived       BOOLEAN NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

-- Per-image attribute confidence scores from vision models
CREATE SEQUENCE IF NOT EXISTS seq_image_attribute_sk START 1;

CREATE TABLE IF NOT EXISTS feature_image_attribute (
    image_attribute_sk  BIGINT PRIMARY KEY DEFAULT nextval('seq_image_attribute_sk'),
    image_sk            BIGINT NOT NULL,
    attribute_code      TEXT NOT NULL,
    confidence_score    DOUBLE NOT NULL,
    classification      TEXT NOT NULL,
    label_source        TEXT NOT NULL DEFAULT 'vision_model',
    model_name          TEXT,
    model_version       TEXT,
    run_id              TEXT,
    is_accepted         BOOLEAN NOT NULL DEFAULT false,
    is_manual_override  BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Voting scenario (a collection of voting blocks)
CREATE TABLE IF NOT EXISTS dim_voting_scenario (
    scenario_id     TEXT PRIMARY KEY,
    scenario_name   TEXT NOT NULL,
    description     TEXT,
    seed            INTEGER,
    config_hash     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    created_by      TEXT DEFAULT 'pipeline'
);

-- Voting block within a scenario
CREATE SEQUENCE IF NOT EXISTS seq_voting_block_sk START 1;

CREATE TABLE IF NOT EXISTS dim_voting_block (
    voting_block_sk     BIGINT PRIMARY KEY DEFAULT nextval('seq_voting_block_sk'),
    block_id            TEXT NOT NULL,
    scenario_id         TEXT NOT NULL,
    block_label         TEXT NOT NULL,
    voter_count         INTEGER NOT NULL,
    votes_per_voter     INTEGER NOT NULL,
    preference_weight   DOUBLE NOT NULL DEFAULT 0.0,
    randomness_weight   DOUBLE NOT NULL DEFAULT 1.0,
    description         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (scenario_id, block_id)
);

-- Preference rules per block
CREATE SEQUENCE IF NOT EXISTS seq_voting_block_rule_sk START 1;

CREATE TABLE IF NOT EXISTS voting_block_rule (
    voting_block_rule_sk BIGINT PRIMARY KEY DEFAULT nextval('seq_voting_block_rule_sk'),
    block_id             TEXT NOT NULL,
    scenario_id          TEXT NOT NULL,
    rule_type            TEXT NOT NULL,
    attribute_code       TEXT NOT NULL,
    rule_weight          DOUBLE DEFAULT 1.0,
    created_at           TIMESTAMPTZ DEFAULT now()
);

-- Voter-to-block assignment
CREATE TABLE IF NOT EXISTS synthetic_voter_block_assignment (
    voter_sk            BIGINT NOT NULL,
    synthetic_run_id    TEXT NOT NULL,
    scenario_id         TEXT NOT NULL,
    block_id            TEXT NOT NULL,
    synthetic_profile_code TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (voter_sk, synthetic_run_id)
);

-- Mart: voting block summary
CREATE TABLE IF NOT EXISTS mart_voting_block_summary (
    scenario_id         TEXT NOT NULL,
    block_id            TEXT NOT NULL,
    voter_count         INTEGER,
    vote_count          INTEGER,
    selected_image_count INTEGER,
    selection_rate      DOUBLE,
    expected_selection_rate DOUBLE,
    lift_over_baseline  DOUBLE,
    top_selected_images_json TEXT,
    top_rejected_images_json TEXT,
    dominant_attributes_json TEXT,
    dominant_clusters_json TEXT,
    detection_status    TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_id)
);

-- Mart: attribute lift per block
CREATE TABLE IF NOT EXISTS mart_voting_block_attribute_lift (
    scenario_id             TEXT NOT NULL,
    block_id                TEXT NOT NULL,
    attribute_code          TEXT NOT NULL,
    block_selection_rate    DOUBLE,
    global_selection_rate   DOUBLE,
    lift                    DOUBLE,
    odds_ratio              DOUBLE,
    selected_count          INTEGER,
    exposed_count           INTEGER,
    confidence_interval_low DOUBLE,
    confidence_interval_high DOUBLE,
    created_at              TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_id, attribute_code)
);

-- Mart: cluster lift per block
CREATE TABLE IF NOT EXISTS mart_voting_block_cluster_lift (
    scenario_id             TEXT NOT NULL,
    block_id                TEXT NOT NULL,
    cluster_id              INTEGER NOT NULL,
    cluster_label           TEXT,
    block_selection_rate    DOUBLE,
    global_selection_rate   DOUBLE,
    lift                    DOUBLE,
    chi_square_contribution DOUBLE,
    selected_count          INTEGER,
    expected_count          DOUBLE,
    created_at              TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_id, cluster_id)
);

-- Mart: image-level lift per block
CREATE TABLE IF NOT EXISTS mart_voting_block_image_lift (
    scenario_id     TEXT NOT NULL,
    block_id        TEXT NOT NULL,
    image_sk        BIGINT NOT NULL,
    block_selection_rate DOUBLE,
    global_selection_rate DOUBLE,
    lift            DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_id, image_sk)
);

-- Mart: block-pair similarity
CREATE TABLE IF NOT EXISTS mart_voting_block_similarity (
    scenario_id             TEXT NOT NULL,
    block_a                 TEXT NOT NULL,
    block_b                 TEXT NOT NULL,
    jaccard_top_n           DOUBLE,
    cosine_similarity       DOUBLE,
    score_correlation       DOUBLE,
    top_image_overlap_count INTEGER,
    top_cluster_overlap_count INTEGER,
    created_at              TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_a, block_b)
);

-- Mart: score impact per block
CREATE TABLE IF NOT EXISTS mart_voting_block_score_impact (
    scenario_id         TEXT NOT NULL,
    block_id            TEXT NOT NULL,
    image_sk            BIGINT NOT NULL,
    score_with_block    DOUBLE,
    score_without_block DOUBLE,
    score_delta         DOUBLE,
    rank_with_block     INTEGER,
    rank_without_block  INTEGER,
    rank_delta          INTEGER,
    block_influence_score DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (scenario_id, block_id, image_sk)
);

-- Mart: calendar impact per scenario
CREATE TABLE IF NOT EXISTS mart_voting_block_calendar_impact (
    scenario_id                     TEXT PRIMARY KEY,
    selected_images_with_json       TEXT,
    selected_images_without_json    TEXT,
    cover_image_with                BIGINT,
    cover_image_without             BIGINT,
    changed_month_count             INTEGER,
    changed_cover_flag              BOOLEAN,
    diversity_score_delta           DOUBLE,
    attribute_distribution_delta_json TEXT,
    cluster_distribution_delta_json TEXT,
    created_at                      TIMESTAMPTZ DEFAULT now()
);
