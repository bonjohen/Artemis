"""Deduplication summary API routes."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/dedup", tags=["dedup"])


@router.get("/summary")
def dedup_summary(
    top_groups: int = Query(5, ge=0, le=20),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return dedup statistics with top group representatives."""
    groups = conn.execute("SELECT count(*) FROM dedup_image_group").fetchone()[0]
    suppressed = conn.execute(
        "SELECT count(*) FROM dim_image WHERE is_suppressed = true"
    ).fetchone()[0]
    active = conn.execute(
        "SELECT count(*) FROM dim_image WHERE vote_pool_flag = true AND COALESCE(is_suppressed, false) = false"
    ).fetchone()[0]
    total = conn.execute(
        "SELECT count(*) FROM dim_image WHERE vote_pool_flag = true"
    ).fetchone()[0]

    threshold = None
    run_row = conn.execute(
        "SELECT similarity_threshold FROM dedup_image_group LIMIT 1"
    ).fetchone()
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
