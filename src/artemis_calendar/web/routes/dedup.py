"""Deduplication summary API routes."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/dedup", tags=["dedup"])


@router.get("/summary")
def dedup_summary(
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return dedup statistics."""
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

    return {
        "groups": int(groups),
        "suppressed": int(suppressed),
        "active": int(active),
        "total": int(total),
        "threshold": threshold,
    }
