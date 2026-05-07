-- Mart: image preference scores (one row per image per scoring run)
CREATE TABLE IF NOT EXISTS mart_image_preference_score (
    score_run_id        TEXT NOT NULL,
    image_sk            BIGINT NOT NULL,
    shown_count         INTEGER,
    selected_count      INTEGER,
    selection_rate      DOUBLE,
    wilson_lower        DOUBLE,
    elo_score           DOUBLE,
    pairwise_wins       INTEGER,
    pairwise_losses     INTEGER,
    btl_score           DOUBLE,
    borda_score         DOUBLE,
    posterior_mean      DOUBLE,
    posterior_lower     DOUBLE,
    posterior_upper     DOUBLE,
    uncertainty_score   DOUBLE,
    polarization_score  DOUBLE,
    broad_appeal_score  DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (score_run_id, image_sk)
);

-- Mart: inter-rater reliability (one row per run, vote mode, optional category)
CREATE TABLE IF NOT EXISTS mart_inter_rater_reliability (
    irr_run_id          TEXT NOT NULL,
    vote_mode           TEXT NOT NULL,
    category_sk         BIGINT,
    image_count         INTEGER,
    voter_count         INTEGER,
    rating_density      DOUBLE,
    krippendorff_alpha  DOUBLE,
    fleiss_kappa        DOUBLE,
    kendall_w           DOUBLE,
    spearman_mean       DOUBLE,
    method_notes        TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (irr_run_id, vote_mode)
);
