"""Stats dashboard API route."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from artemis_calendar.config.sql_helpers import LATEST_SCORE_RUN
from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats(conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    result: dict = {}

    # Reliability metrics
    try:
        rows = conn.execute("SELECT vote_mode, alpha_value FROM mart_inter_rater_reliability").fetchall()
        result["reliability"] = {r[0]: float(r[1]) if r[1] is not None else None for r in rows}
    except duckdb.CatalogException:
        result["reliability"] = {}

    # Bias detection results
    try:
        row = conn.execute(
            """
            SELECT position_bias_coeff, position_bias_pvalue,
                   cluster_bias_chi2, cluster_bias_pvalue,
                   score_vs_truth_spearman, score_vs_truth_pvalue,
                   voter_segment_count
            FROM mart_bias_detection
            ORDER BY created_at DESC LIMIT 1
            """
        ).fetchone()
        if row:
            result["bias"] = {
                "position_bias_coeff": float(row[0]) if row[0] is not None else None,
                "position_bias_pvalue": float(row[1]) if row[1] is not None else None,
                "cluster_bias_chi2": float(row[2]) if row[2] is not None else None,
                "cluster_bias_pvalue": float(row[3]) if row[3] is not None else None,
                "score_vs_truth_spearman": float(row[4]) if row[4] is not None else None,
                "score_vs_truth_pvalue": float(row[5]) if row[5] is not None else None,
                "voter_segment_count": int(row[6]) if row[6] is not None else None,
            }
        else:
            result["bias"] = {}
    except duckdb.CatalogException:
        result["bias"] = {}

    # Score distribution (histogram buckets)
    try:
        rows = conn.execute(
            f"""
            SELECT
                FLOOR(posterior_mean * 20) / 20 AS bucket,
                COUNT(*) AS count
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
            GROUP BY bucket
            ORDER BY bucket
            """
        ).fetchall()
        result["score_distribution"] = [{"bucket": float(r[0]), "count": int(r[1])} for r in rows]
    except duckdb.CatalogException:
        result["score_distribution"] = []

    # Vote counts
    try:
        counts = {}
        for table, label in [
            ("fact_batch_ballot", "batch_ballots"),
            ("fact_pairwise_vote", "pairwise_votes"),
            ("fact_category_ranking", "category_rankings"),
        ]:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[label] = int(row[0])
            except duckdb.CatalogException:
                counts[label] = 0
        result["vote_counts"] = counts
    except Exception:
        result["vote_counts"] = {}

    # Image count
    try:
        row = conn.execute("SELECT COUNT(*) FROM dim_image WHERE vote_pool = true").fetchone()
        result["image_count"] = int(row[0])
    except duckdb.CatalogException:
        result["image_count"] = 0

    return result
