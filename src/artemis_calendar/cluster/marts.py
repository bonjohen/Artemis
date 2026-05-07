"""Build cluster mart tables from feature_image_cluster and related features."""

from __future__ import annotations

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.cluster.marts")


def build_cluster_summary(conn: duckdb.DuckDBPyConnection, cluster_run_id: str) -> int:
    """Build mart_image_cluster_summary for a given cluster run.

    Returns count of rows inserted.
    """
    # Clear previous entries for this run
    conn.execute("DELETE FROM mart_image_cluster_summary WHERE cluster_run_id = ?", [cluster_run_id])

    conn.execute(
        """
        INSERT INTO mart_image_cluster_summary (
            cluster_run_id, cluster_type, cluster_id, image_count,
            top_image_sk, mean_sentiment_score
        )
        SELECT
            fic.cluster_run_id,
            fic.cluster_type,
            fic.cluster_id,
            COUNT(*) AS image_count,
            -- top image = closest to centroid (min distance)
            (SELECT fic2.image_sk
             FROM feature_image_cluster fic2
             WHERE fic2.cluster_run_id = fic.cluster_run_id
               AND fic2.cluster_type = fic.cluster_type
               AND fic2.cluster_id = fic.cluster_id
               AND fic2.distance_to_centroid IS NOT NULL
             ORDER BY fic2.distance_to_centroid ASC
             LIMIT 1) AS top_image_sk,
            AVG(fdt.sentiment_score) AS mean_sentiment_score
        FROM feature_image_cluster fic
        LEFT JOIN feature_description_text fdt ON fdt.image_sk = fic.image_sk
        WHERE fic.cluster_run_id = ?
          AND fic.cluster_id >= 0  -- exclude HDBSCAN noise
        GROUP BY fic.cluster_run_id, fic.cluster_type, fic.cluster_id
        """,
        [cluster_run_id],
    )

    count = conn.execute(
        "SELECT count(*) FROM mart_image_cluster_summary WHERE cluster_run_id = ?",
        [cluster_run_id],
    ).fetchone()[0]

    logger.info(f"Built cluster summary: {count} clusters for run {cluster_run_id}")
    return count


def build_cluster_top_images(conn: duckdb.DuckDBPyConnection, cluster_run_id: str, top_n: int = 5) -> int:
    """Build mart_cluster_top_images — top N images per cluster ranked by distance to centroid.

    Score columns (preference_score, selection_rate, elo_score, borda_score) are NULL
    until Phase 3 statistical modeling backfills them.

    Returns count of rows inserted.
    """
    # Clear previous entries
    conn.execute("DELETE FROM mart_cluster_top_images WHERE cluster_run_id = ?", [cluster_run_id])

    # Compute ranks per cluster, then insert row by row
    # (DuckDB has a known issue with ROW_NUMBER + composite PK binding)
    ranked = conn.execute(
        """
        SELECT cluster_run_id, cluster_type, cluster_id, image_sk, distance_to_centroid
        FROM feature_image_cluster
        WHERE cluster_run_id = ?
          AND cluster_id >= 0
        ORDER BY cluster_type, cluster_id, distance_to_centroid ASC NULLS LAST
        """,
        [cluster_run_id],
    ).fetchall()

    # Group by (cluster_type, cluster_id) and assign ranks
    from itertools import groupby
    from operator import itemgetter

    for (_ctype, _cid), group in groupby(ranked, key=itemgetter(1, 2)):
        for rank, row in enumerate(group, 1):
            if rank > top_n:
                break
            conn.execute(
                """
                INSERT INTO mart_cluster_top_images (
                    cluster_run_id, cluster_type, cluster_id, image_sk, rank_in_cluster
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [row[0], row[1], row[2], row[3], rank],
            )

    count = conn.execute(
        "SELECT count(*) FROM mart_cluster_top_images WHERE cluster_run_id = ?",
        [cluster_run_id],
    ).fetchone()[0]

    logger.info(f"Built top images: {count} rows for run {cluster_run_id}")
    return count
