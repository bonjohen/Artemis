"""Candidate calendar API routes — reuses review/queries.py."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from artemis_calendar.review.queries import (
    fetch_all_candidates,
    fetch_candidate_images,
    fetch_cluster_alternatives,
    resolve_run_id,
)
from artemis_calendar.web.db import get_db
from artemis_calendar.web.models import (
    CandidateDetail,
    CandidateResponse,
    ClusterAlternativeResponse,
    MonthImageResponse,
)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateResponse])
def list_candidates(conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    run_id = resolve_run_id(conn, None)
    candidates = fetch_all_candidates(conn, run_id)
    return [
        CandidateResponse(
            candidate_name=c.candidate_name,
            cover_image_sk=c.cover_image_sk,
            objective_score=c.objective_score,
            popularity_score=c.popularity_score,
            diversity_score=c.diversity_score,
            month_fit_score=c.month_fit_score,
            cover_fit_score=c.cover_fit_score,
            redundancy_penalty=c.redundancy_penalty,
            uncertainty_penalty=c.uncertainty_penalty,
        )
        for c in candidates
    ]


@router.get("/{name}", response_model=CandidateDetail)
def get_candidate(name: str, conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
    run_id = resolve_run_id(conn, None)
    candidates = fetch_all_candidates(conn, run_id)
    candidate = next((c for c in candidates if c.candidate_name == name), None)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate '{name}' not found")

    images = fetch_candidate_images(conn, run_id, name)
    image_responses = [
        MonthImageResponse(
            sequence_number=img.sequence_number,
            month_label=img.month_label,
            image_sk=img.image_sk,
            source_image_id=img.source_image_id,
            title=img.title,
            description=img.description,
            month_fit_score=img.month_fit_score,
            preference_score=img.preference_score,
            brightness_score=img.brightness_score,
            contrast_score=img.contrast_score,
            saturation_score=img.saturation_score,
            dominant_color_json=img.dominant_color_json,
            cluster_id=img.cluster_id,
            broad_appeal_score=img.broad_appeal_score,
            uncertainty_score=img.uncertainty_score,
        )
        for img in images
    ]

    alternatives: dict[int, list[ClusterAlternativeResponse]] = {}
    for img in images:
        if img.cluster_id is not None:
            alts = fetch_cluster_alternatives(conn, run_id, name, img.image_sk, img.cluster_id)
            alternatives[img.image_sk] = [
                ClusterAlternativeResponse(
                    image_sk=a.image_sk,
                    source_image_id=a.source_image_id,
                    preference_score=a.preference_score,
                    broad_appeal_score=a.broad_appeal_score,
                )
                for a in alts
            ]

    return CandidateDetail(
        candidate=CandidateResponse(
            candidate_name=candidate.candidate_name,
            cover_image_sk=candidate.cover_image_sk,
            objective_score=candidate.objective_score,
            popularity_score=candidate.popularity_score,
            diversity_score=candidate.diversity_score,
            month_fit_score=candidate.month_fit_score,
            cover_fit_score=candidate.cover_fit_score,
            redundancy_penalty=candidate.redundancy_penalty,
            uncertainty_penalty=candidate.uncertainty_penalty,
        ),
        images=image_responses,
        alternatives=alternatives,
    )
