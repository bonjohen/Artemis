-- Validation mart tables for S3 (bias detection) and S4 (calendar optimization validation)

CREATE TABLE IF NOT EXISTS mart_bias_detection (
    detection_run_id TEXT PRIMARY KEY,
    score_run_id TEXT,
    position_bias_coeff DOUBLE,
    position_bias_pvalue DOUBLE,
    position_bias_detected BOOLEAN,
    pairwise_left_win_rate DOUBLE,
    pairwise_left_pvalue DOUBLE,
    cluster_bias_chi2 DOUBLE,
    cluster_bias_pvalue DOUBLE,
    voter_segment_count INTEGER,
    voter_consensus_std DOUBLE,
    score_vs_truth_spearman DOUBLE,
    score_vs_truth_pvalue DOUBLE,
    alpha_all_voters DOUBLE,
    alpha_excluding_biased DOUBLE,
    alpha_delta DOUBLE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mart_calendar_validation (
    validation_run_id TEXT,
    candidate_name TEXT,
    gt_cover_recovered BOOLEAN,
    gt_month_recovered INTEGER,
    gt_month_total INTEGER,
    gt_recovery_rate DOUBLE,
    slate_cluster_count INTEGER,
    slate_max_cosine_sim DOUBLE,
    objective_score DOUBLE,
    popularity_score DOUBLE,
    diversity_score DOUBLE,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (validation_run_id, candidate_name)
);
