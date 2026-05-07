-- Voter dimension
CREATE SEQUENCE IF NOT EXISTS seq_voter_sk START 1;

CREATE TABLE IF NOT EXISTS dim_voter (
    voter_sk                BIGINT PRIMARY KEY DEFAULT nextval('seq_voter_sk'),
    voter_public_hash       TEXT,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    synthetic_profile_code  TEXT,
    first_seen_at           TIMESTAMPTZ DEFAULT now(),
    last_seen_at            TIMESTAMPTZ DEFAULT now(),
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Vote sessions
CREATE SEQUENCE IF NOT EXISTS seq_vote_session_sk START 1;

CREATE TABLE IF NOT EXISTS fact_vote_session (
    vote_session_sk         BIGINT PRIMARY KEY DEFAULT nextval('seq_vote_session_sk'),
    voter_sk                BIGINT NOT NULL,
    vote_mode               TEXT NOT NULL,
    category_key            TEXT,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Batch ballots
CREATE SEQUENCE IF NOT EXISTS seq_batch_ballot_sk START 1;

CREATE TABLE IF NOT EXISTS fact_batch_ballot (
    batch_ballot_sk         BIGINT PRIMARY KEY DEFAULT nextval('seq_batch_ballot_sk'),
    vote_session_sk         BIGINT NOT NULL,
    voter_sk                BIGINT NOT NULL,
    shown_count             INTEGER NOT NULL,
    selected_count          INTEGER NOT NULL,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Batch ballot images (one row per shown image)
CREATE SEQUENCE IF NOT EXISTS seq_batch_ballot_image_sk START 1;

CREATE TABLE IF NOT EXISTS fact_batch_ballot_image (
    batch_ballot_image_sk   BIGINT PRIMARY KEY DEFAULT nextval('seq_batch_ballot_image_sk'),
    batch_ballot_sk         BIGINT NOT NULL,
    voter_sk                BIGINT NOT NULL,
    image_sk                BIGINT NOT NULL,
    display_position        INTEGER,
    was_selected            BOOLEAN NOT NULL,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Pairwise votes
CREATE SEQUENCE IF NOT EXISTS seq_pairwise_vote_sk START 1;

CREATE TABLE IF NOT EXISTS fact_pairwise_vote (
    pairwise_vote_sk        BIGINT PRIMARY KEY DEFAULT nextval('seq_pairwise_vote_sk'),
    vote_session_sk         BIGINT NOT NULL,
    voter_sk                BIGINT NOT NULL,
    winner_image_sk         BIGINT NOT NULL,
    loser_image_sk          BIGINT NOT NULL,
    left_image_sk           BIGINT,
    right_image_sk          BIGINT,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Category rankings
CREATE SEQUENCE IF NOT EXISTS seq_category_ranking_sk START 1;

CREATE TABLE IF NOT EXISTS fact_category_ranking (
    category_ranking_sk     BIGINT PRIMARY KEY DEFAULT nextval('seq_category_ranking_sk'),
    vote_session_sk         BIGINT NOT NULL,
    voter_sk                BIGINT NOT NULL,
    category_key            TEXT NOT NULL,
    ranked_count            INTEGER NOT NULL,
    synthetic_flag          BOOLEAN DEFAULT false,
    synthetic_run_id        TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Category ranking images
CREATE SEQUENCE IF NOT EXISTS seq_category_ranking_image_sk START 1;

CREATE TABLE IF NOT EXISTS fact_category_ranking_image (
    category_ranking_image_sk  BIGINT PRIMARY KEY DEFAULT nextval('seq_category_ranking_image_sk'),
    category_ranking_sk        BIGINT NOT NULL,
    voter_sk                   BIGINT NOT NULL,
    category_key               TEXT NOT NULL,
    image_sk                   BIGINT NOT NULL,
    rank_position              INTEGER NOT NULL,
    borda_score                DOUBLE,
    synthetic_flag             BOOLEAN DEFAULT false,
    synthetic_run_id           TEXT,
    created_at                 TIMESTAMPTZ DEFAULT now()
);

-- Synthetic ground truth (restricted — not used during model fitting)
CREATE TABLE IF NOT EXISTS synthetic_image_truth (
    synthetic_run_id           TEXT NOT NULL,
    image_sk                   BIGINT NOT NULL,
    latent_general_appeal      DOUBLE,
    latent_visual_drama        DOUBLE,
    latent_cover_value         DOUBLE,
    ground_truth_calendar_role TEXT,
    PRIMARY KEY (synthetic_run_id, image_sk)
);
