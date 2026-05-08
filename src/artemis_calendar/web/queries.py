"""Database queries for the web API — image browsing, detail, stats."""

from __future__ import annotations

import duckdb

from artemis_calendar.config.sql_helpers import ACTIVE_IMAGE_FILTER, LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN


def fetch_images_page(
    conn: duckdb.DuckDBPyConnection,
    page: int = 1,
    per_page: int = 60,
    sort: str = "score",
    cluster_id: int | None = None,
    min_score: float | None = None,
) -> tuple[list[dict], int]:
    """Fetch a page of images with summary info. Returns (items, total_count)."""
    sort_map = {
        "score": "COALESCE(p.posterior_mean, 0) DESC",
        "brightness": "COALESCE(v.brightness_score, 0) DESC",
        "cluster": "COALESCE(c.cluster_id, 999) ASC, COALESCE(p.posterior_mean, 0) DESC",
    }
    order_clause = sort_map.get(sort, sort_map["score"])

    where_parts = ["d.vote_pool_flag = true", ACTIVE_IMAGE_FILTER]
    params: list = []

    if cluster_id is not None:
        where_parts.append("c.cluster_id = ?")
        params.append(cluster_id)

    if min_score is not None:
        where_parts.append("COALESCE(p.posterior_mean, 0) >= ?")
        params.append(min_score)

    where_clause = " AND ".join(where_parts)

    # Count total
    total = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM dim_image d
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = d.image_sk
            AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_cluster c
            ON c.image_sk = d.image_sk
            AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        WHERE {where_clause}
        """,
        params,
    ).fetchone()[0]

    # Fetch page
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT d.image_sk, d.source_image_id, d.title,
               p.posterior_mean, c.cluster_id, v.brightness_score
        FROM dim_image d
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = d.image_sk
            AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_visual v ON v.image_sk = d.image_sk
        LEFT JOIN feature_image_cluster c
            ON c.image_sk = d.image_sk
            AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    ).fetchall()

    items = [
        {
            "image_sk": int(r[0]),
            "source_image_id": r[1],
            "title": r[2],
            "preference_score": float(r[3]) if r[3] is not None else None,
            "cluster_id": int(r[4]) if r[4] is not None else None,
            "brightness_score": float(r[5]) if r[5] is not None else None,
        }
        for r in rows
    ]
    return items, total


def fetch_image_detail(conn: duckdb.DuckDBPyConnection, image_sk: int) -> dict | None:
    """Fetch full detail for a single image."""
    row = conn.execute(
        f"""
        SELECT d.image_sk, d.source_image_id, d.title, d.description,
               p.posterior_mean, p.broad_appeal_score, p.uncertainty_score,
               p.elo_score, p.borda_score,
               v.brightness_score, v.contrast_score, v.saturation_score,
               v.dominant_color_json,
               c.cluster_id
        FROM dim_image d
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = d.image_sk
            AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_visual v ON v.image_sk = d.image_sk
        LEFT JOIN feature_image_cluster c
            ON c.image_sk = d.image_sk
            AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        WHERE d.image_sk = ?
        """,
        [image_sk],
    ).fetchone()

    if not row:
        return None

    # Get rank
    rank_row = conn.execute(
        f"""
        SELECT rank FROM (
            SELECT image_sk,
                   ROW_NUMBER() OVER (ORDER BY posterior_mean DESC) as rank
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
        ) ranked
        WHERE image_sk = ?
        """,
        [image_sk],
    ).fetchone()

    # Get candidates containing this image
    candidate_rows = conn.execute(
        """
        SELECT DISTINCT candidate_name
        FROM mart_calendar_candidate_month_image
        WHERE image_sk = ?
        ORDER BY candidate_name
        """,
        [image_sk],
    ).fetchall()

    return {
        "image_sk": int(row[0]),
        "source_image_id": row[1],
        "title": row[2],
        "description": row[3],
        "preference_score": float(row[4]) if row[4] is not None else None,
        "broad_appeal_score": float(row[5]) if row[5] is not None else None,
        "uncertainty_score": float(row[6]) if row[6] is not None else None,
        "elo_score": float(row[7]) if row[7] is not None else None,
        "borda_score": float(row[8]) if row[8] is not None else None,
        "rank": int(rank_row[0]) if rank_row else None,
        "brightness_score": float(row[9]) if row[9] is not None else None,
        "contrast_score": float(row[10]) if row[10] is not None else None,
        "saturation_score": float(row[11]) if row[11] is not None else None,
        "dominant_color_json": row[12],
        "cluster_id": int(row[13]) if row[13] is not None else None,
        "candidates": [r[0] for r in candidate_rows],
    }
