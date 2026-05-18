"""Deduplication summary and curation API routes."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/dedup", tags=["dedup"])


@router.get("/summary")
def dedup_summary(
    top_groups: int = Query(5, ge=0, le=20),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return dedup statistics with top group representatives."""
    groups = conn.execute("SELECT count(*) FROM dedup_image_group").fetchone()[0]
    suppressed = conn.execute("SELECT count(*) FROM dim_image WHERE is_suppressed = true").fetchone()[0]
    active = conn.execute(
        "SELECT count(*) FROM dim_image WHERE vote_pool_flag = true AND COALESCE(is_suppressed, false) = false"
    ).fetchone()[0]
    total = conn.execute("SELECT count(*) FROM dim_image WHERE vote_pool_flag = true").fetchone()[0]

    threshold = None
    run_row = conn.execute("SELECT similarity_threshold FROM dedup_image_group LIMIT 1").fetchone()
    if run_row:
        threshold = run_row[0]

    # Top groups by member count with master image info
    top = []
    if top_groups > 0:
        rows = conn.execute(
            """
            SELECT g.group_id, g.master_image_sk, g.member_count,
                   d.source_image_id
            FROM dedup_image_group g
            JOIN dim_image d ON g.master_image_sk = d.image_sk
            ORDER BY g.member_count DESC
            LIMIT ?
            """,
            [top_groups],
        ).fetchall()
        top = [
            {
                "group_id": r[0],
                "master_image_sk": int(r[1]),
                "member_count": int(r[2]),
                "source_image_id": r[3],
            }
            for r in rows
        ]

    return {
        "groups": int(groups),
        "suppressed": int(suppressed),
        "active": int(active),
        "total": int(total),
        "threshold": threshold,
        "top_groups": top,
    }


@router.get("/groups/{group_id}/members")
def dedup_group_members(
    group_id: str,
    limit: int = Query(20, ge=1, le=100),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return member images for a specific duplicate group."""
    group_row = conn.execute(
        "SELECT master_image_sk FROM dedup_image_group WHERE group_id = ?",
        [group_id],
    ).fetchone()
    if not group_row:
        raise HTTPException(status_code=404, detail="Group not found")

    rows = conn.execute(
        """
        SELECT m.image_sk, d.source_image_id, m.is_master,
               round(m.similarity_to_master, 6) AS similarity_to_master
        FROM dedup_image_member m
        JOIN dim_image d ON m.image_sk = d.image_sk
        WHERE m.group_id = ?
        ORDER BY m.is_master DESC, m.similarity_to_master DESC
        LIMIT ?
        """,
        [group_id, limit],
    ).fetchall()

    return {
        "group_id": group_id,
        "master_sk": int(group_row[0]),
        "members": [
            {
                "image_sk": int(r[0]),
                "source_image_id": r[1],
                "is_master": bool(r[2]),
                "similarity_to_master": float(r[3]),
            }
            for r in rows
        ],
    }


@router.get("/distribution")
def dedup_distribution(
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return group size distribution as bucketed histogram."""
    rows = conn.execute(
        """
        SELECT
          CASE
            WHEN member_count = 2 THEN '2'
            WHEN member_count BETWEEN 3 AND 5 THEN '3-5'
            WHEN member_count BETWEEN 6 AND 10 THEN '6-10'
            WHEN member_count BETWEEN 11 AND 25 THEN '11-25'
            WHEN member_count BETWEEN 26 AND 50 THEN '26-50'
            WHEN member_count BETWEEN 51 AND 100 THEN '51-100'
            WHEN member_count BETWEEN 101 AND 500 THEN '101-500'
            ELSE '500+'
          END AS bucket,
          count(*) AS count
        FROM dedup_image_group
        GROUP BY bucket
        ORDER BY min(member_count)
        """
    ).fetchall()

    return [{"bucket": r[0], "count": int(r[1])} for r in rows]


@router.get("/dark-stats")
def dedup_dark_stats(
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return count of near-black images excluded by dark pixel filter."""
    dark_count = conn.execute("SELECT count(*) FROM feature_image_visual WHERE dark_pixel_ratio >= 0.92").fetchone()[0]
    total = conn.execute("SELECT count(*) FROM dim_image WHERE vote_pool_flag = true").fetchone()[0]

    return {
        "dark_count": int(dark_count),
        "threshold": 0.92,
        "total_vote_pool": int(total),
    }
