"""Cluster browsing API routes."""

from __future__ import annotations

import math

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from artemis_calendar.config.sql_helpers import LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN
from artemis_calendar.web.db import get_db
from artemis_calendar.web.models import ImageSummary, PaginatedResponse

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("")
def list_clusters(conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    rows = conn.execute(
        """
        SELECT s.cluster_id, s.image_count, s.mean_preference_score,
               t.source_image_id AS top_image_guid
        FROM mart_image_cluster_summary s
        LEFT JOIN mart_cluster_top_images t
            ON t.cluster_id = s.cluster_id
            AND t.cluster_type = s.cluster_type
            AND t.cluster_run_id = s.cluster_run_id
            AND t.rank = 1
        WHERE s.cluster_type = 'visual'
          AND s.cluster_run_id = (
              SELECT cluster_run_id FROM mart_image_cluster_summary
              WHERE cluster_type = 'visual'
              ORDER BY created_at DESC LIMIT 1
          )
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
        WHERE c.cluster_type = 'visual'
          AND c.cluster_id = ?
          AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
          AND d.vote_pool = true
        """,
        [cluster_id],
    ).fetchone()[0]

    if total == 0:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

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
          AND d.vote_pool = true
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
