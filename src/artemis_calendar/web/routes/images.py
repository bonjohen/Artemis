"""Image browsing and detail API routes."""

from __future__ import annotations

import math

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from artemis_calendar.config.sql_helpers import ACTIVE_IMAGE_FILTER, LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN
from artemis_calendar.web.db import get_db
from artemis_calendar.web.models import ImageDetail, ImageSummary, PaginatedResponse
from artemis_calendar.web.queries import fetch_image_detail, fetch_images_page

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("", response_model=PaginatedResponse)
def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(60, ge=1, le=200),
    sort: str = Query("score"),
    cluster_id: int | None = Query(None),
    min_score: float | None = Query(None),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    items, total = fetch_images_page(conn, page, per_page, sort, cluster_id, min_score)
    pages = max(1, math.ceil(total / per_page))
    return PaginatedResponse(
        items=[ImageSummary(**i) for i in items],
        total=total,
        page=page,
        pages=pages,
    )


@router.get("/{sk}", response_model=ImageDetail)
def get_image(sk: int, conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    detail = fetch_image_detail(conn, sk)
    if not detail:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageDetail(**detail)


@router.get("/timeline/segments")
def timeline_segments(
    segment_size: int = Query(2000, ge=500, le=10000),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),  # noqa: B008
):
    """Return images grouped by frame-number segments for timeline view.

    Each segment includes image count, top attributes, and representative thumbnails.
    """
    rows = conn.execute(
        f"""
        SELECT d.image_sk, d.source_image_id,
               CAST(REPLACE(d.source_image_id, 'ART002-E-', '') AS INTEGER) AS frame,
               COALESCE(p.posterior_mean, 0) AS score,
               c.cluster_id
        FROM dim_image d
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = d.image_sk AND p.score_run_id = {LATEST_SCORE_RUN}
        LEFT JOIN feature_image_visual v ON v.image_sk = d.image_sk
        LEFT JOIN feature_image_cluster c
            ON c.image_sk = d.image_sk AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        WHERE d.vote_pool_flag = true AND {ACTIVE_IMAGE_FILTER}
        ORDER BY frame
        """
    ).fetchall()

    if not rows:
        return []

    frames = [int(r[2]) for r in rows]
    min_frame = min(frames)
    max_frame = max(frames)

    # Build segments
    segments = []
    seg_start = (min_frame // segment_size) * segment_size

    while seg_start <= max_frame:
        seg_end = seg_start + segment_size
        seg_rows = [r for r in rows if seg_start <= int(r[2]) < seg_end]

        if seg_rows:
            # Top attributes for this segment
            image_sks = [int(r[0]) for r in seg_rows]
            placeholders = ", ".join("?" * len(image_sks))
            attr_rows = conn.execute(
                f"""
                SELECT attribute_code, count(*) as cnt
                FROM feature_image_attribute
                WHERE image_sk IN ({placeholders})
                  AND label_source = 'clip_zero_shot' AND is_accepted = true
                GROUP BY attribute_code
                ORDER BY cnt DESC LIMIT 5
                """,
                image_sks,
            ).fetchall()

            # Pick representative thumbnails: highest-scoring images
            sorted_rows = sorted(seg_rows, key=lambda r: -r[3])
            thumbs = [
                {
                    "image_sk": int(r[0]),
                    "source_image_id": r[1],
                    "score": round(float(r[3]), 3),
                }
                for r in sorted_rows[:8]
            ]

            segments.append(
                {
                    "start_frame": seg_start,
                    "end_frame": seg_end,
                    "label": f"E-{seg_start}–{seg_end - 1}",
                    "image_count": len(seg_rows),
                    "top_attributes": [{"code": r[0], "count": int(r[1])} for r in attr_rows],
                    "thumbnails": thumbs,
                }
            )

        seg_start = seg_end

    return {
        "segment_size": segment_size,
        "total_images": len(rows),
        "frame_range": [min_frame, max_frame],
        "segments": segments,
    }
