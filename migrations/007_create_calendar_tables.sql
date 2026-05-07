-- Mart: calendar candidate (one row per selection method per optimization run)
CREATE TABLE IF NOT EXISTS mart_calendar_candidate (
    candidate_run_id    TEXT NOT NULL,
    candidate_name      TEXT NOT NULL,
    cover_image_sk      BIGINT,
    objective_score     DOUBLE,
    popularity_score    DOUBLE,
    diversity_score     DOUBLE,
    month_fit_score     DOUBLE,
    cover_fit_score     DOUBLE,
    redundancy_penalty  DOUBLE,
    uncertainty_penalty DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (candidate_run_id, candidate_name)
);

-- Mart: calendar candidate month-image assignments (13 rows per candidate)
CREATE TABLE IF NOT EXISTS mart_calendar_candidate_month_image (
    candidate_run_id    TEXT NOT NULL,
    candidate_name      TEXT NOT NULL,
    sequence_number     INTEGER NOT NULL,
    month_label         TEXT NOT NULL,
    image_sk            BIGINT NOT NULL,
    month_fit_score     DOUBLE,
    preference_score    DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (candidate_run_id, candidate_name, sequence_number)
);
