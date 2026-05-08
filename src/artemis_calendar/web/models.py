"""Pydantic response schemas for the web API."""

from __future__ import annotations

from pydantic import BaseModel


class ImageSummary(BaseModel):
    image_sk: int
    source_image_id: str
    title: str | None = None
    preference_score: float | None = None
    cluster_id: int | None = None
    brightness_score: float | None = None


class ImageDetail(BaseModel):
    image_sk: int
    source_image_id: str
    title: str | None = None
    description: str | None = None
    preference_score: float | None = None
    broad_appeal_score: float | None = None
    uncertainty_score: float | None = None
    elo_score: float | None = None
    borda_score: float | None = None
    rank: int | None = None
    brightness_score: float | None = None
    contrast_score: float | None = None
    saturation_score: float | None = None
    dominant_color_json: str | None = None
    cluster_id: int | None = None
    candidates: list[str] = []


class PaginatedResponse(BaseModel):
    items: list[ImageSummary]
    total: int
    page: int
    pages: int


class MonthImageResponse(BaseModel):
    sequence_number: int
    month_label: str
    image_sk: int
    source_image_id: str
    title: str | None = None
    description: str | None = None
    month_fit_score: float = 0.0
    preference_score: float = 0.0
    brightness_score: float | None = None
    contrast_score: float | None = None
    saturation_score: float | None = None
    dominant_color_json: str | None = None
    cluster_id: int | None = None
    broad_appeal_score: float | None = None
    uncertainty_score: float | None = None


class ClusterAlternativeResponse(BaseModel):
    image_sk: int
    source_image_id: str
    preference_score: float = 0.0
    broad_appeal_score: float | None = None


class CandidateResponse(BaseModel):
    candidate_name: str
    cover_image_sk: int
    objective_score: float = 0.0
    popularity_score: float = 0.0
    diversity_score: float = 0.0
    month_fit_score: float = 0.0
    cover_fit_score: float = 0.0
    redundancy_penalty: float = 0.0
    uncertainty_penalty: float = 0.0


class CandidateDetail(BaseModel):
    candidate: CandidateResponse
    images: list[MonthImageResponse]
    alternatives: dict[int, list[ClusterAlternativeResponse]] = {}
