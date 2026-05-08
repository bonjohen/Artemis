"""Image browsing and detail API routes."""

from __future__ import annotations

import math

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

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
