"""Write calendar optimization results to mart tables."""

from __future__ import annotations

import duckdb
import pyarrow as pa

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.optimize.marts")


def write_calendar_candidates(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    candidates: list[dict],
) -> int:
    """Write candidate calendars to mart_calendar_candidate.

    Each candidate dict must have: candidate_name, cover_image_sk,
    objective_score, popularity_score, diversity_score, month_fit_score,
    cover_fit_score, redundancy_penalty, uncertainty_penalty.

    Returns count of rows written.
    """
    conn.execute("DELETE FROM mart_calendar_candidate WHERE candidate_run_id = ?", [run_id])

    if not candidates:
        return 0

    tbl = pa.table(
        {  # noqa: F841 — referenced by DuckDB SQL below
            "candidate_run_id": [run_id] * len(candidates),
            "candidate_name": [c["candidate_name"] for c in candidates],
            "cover_image_sk": [c["cover_image_sk"] for c in candidates],
            "objective_score": [c["objective_score"] for c in candidates],
            "popularity_score": [c["popularity_score"] for c in candidates],
            "diversity_score": [c["diversity_score"] for c in candidates],
            "month_fit_score": [c["month_fit_score"] for c in candidates],
            "cover_fit_score": [c["cover_fit_score"] for c in candidates],
            "redundancy_penalty": [c["redundancy_penalty"] for c in candidates],
            "uncertainty_penalty": [c["uncertainty_penalty"] for c in candidates],
        }
    )

    columns = ", ".join(
        [
            "candidate_run_id",
            "candidate_name",
            "cover_image_sk",
            "objective_score",
            "popularity_score",
            "diversity_score",
            "month_fit_score",
            "cover_fit_score",
            "redundancy_penalty",
            "uncertainty_penalty",
        ]
    )
    conn.execute(f"INSERT INTO mart_calendar_candidate ({columns}) SELECT * FROM tbl")

    logger.info(f"Wrote {len(candidates)} calendar candidates for run {run_id}")
    return len(candidates)


def write_calendar_month_images(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    candidate_name: str,
    assignments: list[tuple[int, int, str]],
    month_fit_scores: dict[int, float],
    preference_scores: dict[int, float],
) -> int:
    """Write month-image assignments for a candidate calendar.

    assignments: list of (image_sk, sequence_number, month_label).

    Returns count of rows written.
    """
    if not assignments:
        return 0

    tbl = pa.table(
        {  # noqa: F841 — referenced by DuckDB SQL below
            "candidate_run_id": [run_id] * len(assignments),
            "candidate_name": [candidate_name] * len(assignments),
            "sequence_number": [a[1] for a in assignments],
            "month_label": [a[2] for a in assignments],
            "image_sk": [a[0] for a in assignments],
            "month_fit_score": [month_fit_scores.get(a[0], 0.0) for a in assignments],
            "preference_score": [preference_scores.get(a[0], 0.0) for a in assignments],
        }
    )

    columns = ", ".join(
        [
            "candidate_run_id",
            "candidate_name",
            "sequence_number",
            "month_label",
            "image_sk",
            "month_fit_score",
            "preference_score",
        ]
    )
    conn.execute(f"INSERT INTO mart_calendar_candidate_month_image ({columns}) SELECT * FROM tbl")

    return len(assignments)
