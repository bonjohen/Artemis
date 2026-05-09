"""Cluster browsing API routes."""

from __future__ import annotations

import math

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from artemis_calendar.config.sql_helpers import ACTIVE_IMAGE_FILTER, LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN
from artemis_calendar.web.db import get_db
from artemis_calendar.web.models import ImageSummary, PaginatedResponse

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("")
def list_clusters(conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    rows = conn.execute(
        f"""
        SELECT s.cluster_id, s.image_count, s.mean_preference_score,
               d.source_image_id AS top_image_guid
        FROM mart_image_cluster_summary s
        LEFT JOIN mart_cluster_top_images t
            ON t.cluster_id = s.cluster_id
            AND t.cluster_type = s.cluster_type
            AND t.cluster_run_id = s.cluster_run_id
            AND t.rank_in_cluster = 1
        LEFT JOIN dim_image d ON d.image_sk = t.image_sk
        WHERE s.cluster_type = 'visual'
          AND s.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        ORDER BY s.cluster_id
        """
    ).fetchall()
    return [
        {
            "cluster_id": int(r[0]),
            "image_count": int(r[1]),
            "mean_preference_score": float(r[2]) if r[2] is not None else None,
            "top_image_guid": r[3],
        }
        for r in rows
    ]


@router.get("/spotlights")
def all_spotlights(
    diverse_count: int = Query(5, ge=1, le=20),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return spotlight (representative + diverse) for every cluster."""
    cluster_ids = conn.execute(
        f"""
        SELECT DISTINCT cluster_id FROM feature_image_cluster
        WHERE cluster_type = 'visual' AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        ORDER BY cluster_id
        """
    ).fetchall()

    results = []
    for (cid,) in cluster_ids:
        spot = _compute_spotlight(conn, int(cid), diverse_count, allow_empty=True)
        if spot is not None:
            results.append(spot)
    return results


@router.get("/{cluster_id}")
def get_cluster(
    cluster_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(60, ge=1, le=200),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    # Count
    total = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM feature_image_cluster c
        JOIN dim_image d ON d.image_sk = c.image_sk
        LEFT JOIN feature_image_visual v ON v.image_sk = c.image_sk
        WHERE c.cluster_type = 'visual'
          AND c.cluster_id = ?
          AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
          AND d.vote_pool_flag = true
          AND {ACTIVE_IMAGE_FILTER}
        """,
        [cluster_id],
    ).fetchone()[0]

    if total == 0:
        return PaginatedResponse(items=[], total=0, page=1, pages=0)

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT d.image_sk, d.source_image_id, d.title,
               p.posterior_mean, c.cluster_id, v.brightness_score
        FROM feature_image_cluster c
        JOIN dim_image d ON d.image_sk = c.image_sk
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = c.image_sk
            AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_visual v ON v.image_sk = c.image_sk
        WHERE c.cluster_type = 'visual'
          AND c.cluster_id = ?
          AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
          AND d.vote_pool_flag = true
          AND {ACTIVE_IMAGE_FILTER}
        ORDER BY COALESCE(p.posterior_mean, 0) DESC
        LIMIT ? OFFSET ?
        """,
        [cluster_id, per_page, offset],
    ).fetchall()

    items = [
        ImageSummary(
            image_sk=int(r[0]),
            source_image_id=r[1],
            title=r[2],
            preference_score=float(r[3]) if r[3] is not None else None,
            cluster_id=int(r[4]) if r[4] is not None else None,
            brightness_score=float(r[5]) if r[5] is not None else None,
        )
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        pages=max(1, math.ceil(total / per_page)),
    )


@router.get("/{cluster_id}/spotlight")
def cluster_spotlight(
    cluster_id: int,
    diverse_count: int = Query(5, ge=1, le=20),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return 1 representative image + N diverse images for a cluster.

    Representative = closest to centroid.
    Diverse = greedy max-min distance selection from CLIP embeddings.
    """
    return _compute_spotlight(conn, cluster_id, diverse_count)


def _compute_spotlight(
    conn: duckdb.DuckDBPyConnection,
    cluster_id: int,
    diverse_count: int,
    allow_empty: bool = False,
) -> dict | None:
    """Compute representative + diverse images for one cluster."""
    import numpy as np

    # Get all images in cluster with distance, score, and guid
    rows = conn.execute(
        f"""
        SELECT d.image_sk, d.source_image_id,
               c.distance_to_centroid,
               COALESCE(p.posterior_mean, 0) AS score
        FROM feature_image_cluster c
        JOIN dim_image d ON d.image_sk = c.image_sk
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = c.image_sk AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_visual v ON v.image_sk = c.image_sk
        WHERE c.cluster_type = 'visual'
          AND c.cluster_id = ?
          AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
          AND d.vote_pool_flag = true
          AND {ACTIVE_IMAGE_FILTER}
        ORDER BY c.distance_to_centroid ASC
        """,
        [cluster_id],
    ).fetchall()

    if not rows:
        # All images suppressed — find representative from full (unfiltered) cluster
        fallback = conn.execute(
            f"""
            SELECT d.image_sk, d.source_image_id,
                   c.distance_to_centroid,
                   COALESCE(p.posterior_mean, 0) AS score
            FROM feature_image_cluster c
            JOIN dim_image d ON d.image_sk = c.image_sk
            LEFT JOIN mart_image_preference_score p
                ON p.image_sk = c.image_sk AND p.score_run_id = {LATEST_SCORE_RUN}
            WHERE c.cluster_type = 'visual'
              AND c.cluster_id = ?
              AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
              AND d.vote_pool_flag = true
            ORDER BY c.distance_to_centroid ASC
            LIMIT 1
            """,
            [cluster_id],
        ).fetchone()
        if fallback:
            total_in_cluster = conn.execute(
                f"""
                SELECT count(*) FROM feature_image_cluster
                WHERE cluster_type = 'visual' AND cluster_id = ?
                  AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
                """,
                [cluster_id],
            ).fetchone()[0]
            label_row = conn.execute(
                f"""
                SELECT cluster_label FROM mart_image_cluster_summary
                WHERE cluster_type = 'visual' AND cluster_id = ?
                  AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
                """,
                [cluster_id],
            ).fetchone()
            return {
                "cluster_id": cluster_id,
                "cluster_label": label_row[0] if label_row else None,
                "image_count": int(total_in_cluster),
                "all_suppressed": True,
                "representative": {
                    "image_sk": int(fallback[0]),
                    "source_image_id": fallback[1],
                    "preference_score": float(fallback[3]),
                },
                "diverse": [],
            }
        if allow_empty:
            return None
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

    image_sks = [int(r[0]) for r in rows]
    guids = {int(r[0]): r[1] for r in rows}
    scores = {int(r[0]): float(r[3]) for r in rows}

    # Representative = closest to centroid (first row)
    rep_sk = image_sks[0]

    # Load CLIP embeddings for this cluster to compute diversity
    emb_rows = conn.execute(
        """
        SELECT image_sk, embedding_vector
        FROM feature_image_embedding
        WHERE image_sk = ANY(?)
        """,
        [image_sks],
    ).fetchall()

    if len(emb_rows) < 2:
        # Not enough embeddings — fall back to distance-based diversity
        diverse_sks = image_sks[-diverse_count:] if len(image_sks) > 1 else []
    else:
        # Build embedding matrix
        emb_map = {}
        for sk, vec in emb_rows:
            sk = int(sk)
            if isinstance(vec, (list, np.ndarray)):
                emb_map[sk] = np.array(vec, dtype=np.float32)
            else:
                emb_map[sk] = np.frombuffer(vec, dtype=np.float32)

        # Greedy max-min diversity selection
        # Start with representative, then iteratively pick the image
        # most distant from all already-selected images
        available = [sk for sk in image_sks if sk != rep_sk and sk in emb_map]
        if rep_sk not in emb_map:
            diverse_sks = available[:diverse_count]
        else:
            selected = [rep_sk]
            selected_embs = [emb_map[rep_sk]]

            for _ in range(min(diverse_count, len(available))):
                best_sk = None
                best_min_dist = -1.0

                for sk in available:
                    if sk in selected:
                        continue
                    emb = emb_map.get(sk)
                    if emb is None:
                        continue
                    # Min distance to any selected image
                    min_dist = min(
                        float(np.linalg.norm(emb - s_emb))
                        for s_emb in selected_embs
                    )
                    if min_dist > best_min_dist:
                        best_min_dist = min_dist
                        best_sk = sk

                if best_sk is None:
                    break
                selected.append(best_sk)
                selected_embs.append(emb_map[best_sk])

            diverse_sks = selected[1:]  # exclude representative

    def _img_dict(sk):
        return {
            "image_sk": sk,
            "source_image_id": guids.get(sk, ""),
            "preference_score": scores.get(sk),
        }

    # Get cluster label
    label_row = conn.execute(
        f"""
        SELECT cluster_label FROM mart_image_cluster_summary
        WHERE cluster_type = 'visual' AND cluster_id = ?
          AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        """,
        [cluster_id],
    ).fetchone()

    return {
        "cluster_id": cluster_id,
        "cluster_label": label_row[0] if label_row else None,
        "image_count": len(rows),
        "representative": _img_dict(rep_sk),
        "diverse": [_img_dict(sk) for sk in diverse_sks],
    }
