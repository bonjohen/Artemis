"""Category ranking scores: Borda count aggregation."""

from __future__ import annotations

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.category")


def compute_borda_scores(conn: duckdb.DuckDBPyConnection) -> dict[int, dict]:
    """Compute aggregated Borda scores from category ranking data.

    Borda conversion: rank 1 -> 3 points, rank 2 -> 2 points, rank 3 -> 1 point.

    Returns dict keyed by image_sk with keys:
        borda_score (sum of all Borda points across rankings)
        borda_count (number of times ranked)
        borda_mean  (average Borda score per ranking appearance)
    """
    rows = conn.execute(
        """
        SELECT
            image_sk,
            SUM(borda_score) AS total_borda,
            COUNT(*) AS rank_count,
            AVG(borda_score) AS mean_borda
        FROM fact_category_ranking_image
        GROUP BY image_sk
        """
    ).fetchall()

    if not rows:
        logger.warning("No category ranking data found")
        return {}

    scores = {
        int(r[0]): {
            "borda_score": float(r[1]),
            "borda_count": int(r[2]),
            "borda_mean": float(r[3]),
        }
        for r in rows
    }

    logger.info(f"Computed Borda scores for {len(scores)} images")
    return scores
