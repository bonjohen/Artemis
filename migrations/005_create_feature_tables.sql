-- Feature store: visual features
CREATE SEQUENCE IF NOT EXISTS seq_image_visual_feature_sk START 1;

CREATE TABLE IF NOT EXISTS feature_image_visual (
    image_visual_feature_sk BIGINT PRIMARY KEY DEFAULT nextval('seq_image_visual_feature_sk'),
    image_sk                BIGINT NOT NULL,
    feature_run_id          TEXT NOT NULL,
    orientation             TEXT,
    aspect_ratio            DOUBLE,
    brightness_score        DOUBLE,
    contrast_score          DOUBLE,
    saturation_score        DOUBLE,
    dominant_color_json     TEXT,
    has_earth_flag          BOOLEAN,
    has_moon_flag           BOOLEAN,
    has_crew_flag           BOOLEAN,
    has_spacecraft_flag     BOOLEAN,
    aesthetic_tag_json      TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Feature store: text features from descriptions
CREATE SEQUENCE IF NOT EXISTS seq_description_feature_sk START 1;

CREATE TABLE IF NOT EXISTS feature_description_text (
    description_feature_sk  BIGINT PRIMARY KEY DEFAULT nextval('seq_description_feature_sk'),
    image_sk                BIGINT NOT NULL,
    feature_run_id          TEXT NOT NULL,
    description_language    TEXT,
    sentiment_score         DOUBLE,
    subjectivity_score      DOUBLE,
    emotion_json            TEXT,
    topic_terms_json        TEXT,
    entity_json             TEXT,
    mission_phase_label     TEXT,
    month_affinity_json     TEXT,
    cover_affinity_score    DOUBLE,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Feature store: image embeddings (CLIP)
CREATE SEQUENCE IF NOT EXISTS seq_image_embedding_sk START 1;

CREATE TABLE IF NOT EXISTS feature_image_embedding (
    image_embedding_sk      BIGINT PRIMARY KEY DEFAULT nextval('seq_image_embedding_sk'),
    image_sk                BIGINT NOT NULL,
    embedding_model         TEXT NOT NULL,
    embedding_model_version TEXT NOT NULL,
    embedding_vector        FLOAT[] NOT NULL,
    embedding_dimension     INTEGER NOT NULL,
    source_image_hash       TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Feature store: description embeddings (sentence-transformers)
CREATE SEQUENCE IF NOT EXISTS seq_description_embedding_sk START 1;

CREATE TABLE IF NOT EXISTS feature_description_embedding (
    description_embedding_sk BIGINT PRIMARY KEY DEFAULT nextval('seq_description_embedding_sk'),
    image_sk                 BIGINT NOT NULL,
    embedding_model          TEXT NOT NULL,
    embedding_model_version  TEXT NOT NULL,
    text_source              TEXT NOT NULL,
    embedding_vector         FLOAT[] NOT NULL,
    embedding_dimension      INTEGER NOT NULL,
    source_text_hash         TEXT,
    created_at               TIMESTAMPTZ DEFAULT now()
);

-- Feature store: cluster assignments
CREATE SEQUENCE IF NOT EXISTS seq_image_cluster_sk START 1;

CREATE TABLE IF NOT EXISTS feature_image_cluster (
    image_cluster_sk    BIGINT PRIMARY KEY DEFAULT nextval('seq_image_cluster_sk'),
    image_sk            BIGINT NOT NULL,
    cluster_run_id      TEXT NOT NULL,
    cluster_type        TEXT NOT NULL,
    cluster_algorithm   TEXT NOT NULL,
    cluster_id          INTEGER NOT NULL,
    cluster_label       TEXT,
    distance_to_centroid DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Mart: cluster summary
CREATE TABLE IF NOT EXISTS mart_image_cluster_summary (
    cluster_run_id           TEXT NOT NULL,
    cluster_type             TEXT NOT NULL,
    cluster_id               INTEGER NOT NULL,
    cluster_label            TEXT,
    image_count              INTEGER,
    top_image_sk             BIGINT,
    mean_preference_score    DOUBLE,
    max_preference_score     DOUBLE,
    mean_sentiment_score     DOUBLE,
    calendar_candidate_count INTEGER,
    review_priority          TEXT,
    notes                    TEXT,
    PRIMARY KEY (cluster_run_id, cluster_type, cluster_id)
);

-- Mart: top images per cluster
CREATE TABLE IF NOT EXISTS mart_cluster_top_images (
    cluster_run_id     TEXT NOT NULL,
    cluster_type       TEXT NOT NULL,
    cluster_id         INTEGER NOT NULL,
    image_sk           BIGINT NOT NULL,
    rank_in_cluster    INTEGER NOT NULL,
    preference_score   DOUBLE,
    selection_rate     DOUBLE,
    elo_score          DOUBLE,
    borda_score        DOUBLE,
    diversity_value    DOUBLE,
    recommended_action TEXT,
    PRIMARY KEY (cluster_run_id, cluster_type, cluster_id, image_sk)
);
