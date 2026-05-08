"""Attribute distribution API routes."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/attributes", tags=["attributes"])


@router.get("/distribution")
def attribute_distribution(
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return accepted/tentative/rejected counts per attribute code."""
    rows = conn.execute(
        """
        SELECT attribute_code,
               sum(CASE WHEN classification = 'accepted' THEN 1 ELSE 0 END) AS accepted,
               sum(CASE WHEN classification = 'tentative' THEN 1 ELSE 0 END) AS tentative,
               sum(CASE WHEN classification = 'rejected' THEN 1 ELSE 0 END) AS rejected,
               count(*) AS total,
               avg(confidence_score) AS avg_confidence
        FROM feature_image_attribute
        WHERE label_source = 'clip_zero_shot'
        GROUP BY attribute_code
        ORDER BY accepted DESC
        """
    ).fetchall()

    return [
        {
            "code": r[0],
            "accepted": int(r[1]),
            "tentative": int(r[2]),
            "rejected": int(r[3]),
            "total": int(r[4]),
            "avg_confidence": round(float(r[5]), 4) if r[5] else None,
        }
        for r in rows
    ]


@router.get("/derived")
def derived_attribute_counts(
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return counts for derived attributes."""
    rows = conn.execute(
        """
        SELECT attribute_code, count(*) AS count
        FROM feature_image_attribute
        WHERE label_source = 'derived_rule'
        GROUP BY attribute_code
        ORDER BY count DESC
        """
    ).fetchall()

    return [{"code": r[0], "count": int(r[1])} for r in rows]
