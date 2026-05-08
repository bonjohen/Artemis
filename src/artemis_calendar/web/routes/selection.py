"""Interactive selection scoring and persistence API routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from artemis_calendar.config.settings import OUTPUT_ROOT
from artemis_calendar.optimize.scoring import score_calendar

router = APIRouter(prefix="/api/selection", tags=["selection"])

SELECTIONS_DIR = OUTPUT_ROOT / "selections"

MONTH_LABELS = [
    "December 2026",
    "January 2027",
    "February 2027",
    "March 2027",
    "April 2027",
    "May 2027",
    "June 2027",
    "July 2027",
    "August 2027",
    "September 2027",
    "October 2027",
    "November 2027",
    "December 2027",
]


class MonthAssignment(BaseModel):
    image_sk: int
    sequence_number: int


class ScoreRequest(BaseModel):
    assignments: list[MonthAssignment]


class SelectionSave(BaseModel):
    name: str
    assignments: list[MonthAssignment]
    notes: str = ""


@router.post("/score")
def score_selection(body: ScoreRequest, request: Request):
    selected_sks = [a.image_sk for a in body.assignments]
    assignments_tuples = [
        (a.image_sk, a.sequence_number, MONTH_LABELS[a.sequence_number - 1] if a.sequence_number <= 13 else "")
        for a in body.assignments
    ]

    result = score_calendar(
        selected_sks=selected_sks,
        assignments=assignments_tuples,
        preference=request.app.state.preference,
        month_fit=request.app.state.month_fit,
        cover_fit=request.app.state.cover_fit,
        uncertainty=request.app.state.uncertainty,
        clusters=request.app.state.clusters,
        embeddings=request.app.state.embeddings,
    )
    return result


@router.get("")
def get_selection(name: str = "current"):
    path = SELECTIONS_DIR / f"{name}.json"
    if not path.exists():
        return {"name": name, "assignments": [], "notes": ""}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


@router.put("")
def save_selection(body: SelectionSave):
    SELECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SELECTIONS_DIR / f"{body.name}.json"
    data = {
        "name": body.name,
        "assignments": [a.model_dump() for a in body.assignments],
        "notes": body.notes,
        "saved_at": datetime.now(tz=UTC).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"status": "saved", "path": str(path)}


@router.get("/history")
def list_selections():
    if not SELECTIONS_DIR.exists():
        return []
    files = sorted(SELECTIONS_DIR.glob("*.json"))
    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append(
                {
                    "name": data.get("name", f.stem),
                    "saved_at": data.get("saved_at"),
                    "assignment_count": len(data.get("assignments", [])),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return result
