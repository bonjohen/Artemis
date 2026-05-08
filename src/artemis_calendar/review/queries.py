"""Data queries for the review package — all SQL lives here."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from artemis_calendar.config.sql_helpers import LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN


@dataclass
class CandidateScore:
    """Calendar-level scores for one candidate."""

    candidate_name: str
    cover_image_sk: int
    objective_score: float
    popularity_score: float
    diversity_score: float
    month_fit_score: float
    cover_fit_score: float
    redundancy_penalty: float
    uncertainty_penalty: float


@dataclass
class MonthImage:
    """One month-image assignment within a candidate."""

    sequence_number: int
    month_label: str
    image_sk: int
    source_image_id: str  # GUID
    title: str | None
    description: str | None
    month_fit_score: float
    preference_score: float
    brightness_score: float | None
    contrast_score: float | None
    saturation_score: float | None
    dominant_color_json: str | None
    cluster_id: int | None
    broad_appeal_score: float | None
    uncertainty_score: float | None


@dataclass
class ClusterAlternative:
    """An image in the same cluster that was not selected."""

    image_sk: int
    source_image_id: str
    preference_score: float
    broad_appeal_score: float | None


def resolve_run_id(conn: duckdb.DuckDBPyConnection, run_id: str | None) -> str:
    """Resolve run_id to the latest if None."""
    if run_id is not None:
        return run_id
    row = conn.execute(
        "SELECT candidate_run_id FROM mart_calendar_candidate ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise ValueError("No calendar candidates found in warehouse")
    return row[0]


def fetch_all_candidates(conn: duckdb.DuckDBPyConnection, run_id: str) -> list[CandidateScore]:
    """Fetch all candidates for a run with their calendar-level scores."""
    rows = conn.execute(
        """
        SELECT candidate_name, cover_image_sk,
               objective_score, popularity_score, diversity_score,
               month_fit_score, cover_fit_score,
               redundancy_penalty, uncertainty_penalty
        FROM mart_calendar_candidate
        WHERE candidate_run_id = ?
        ORDER BY candidate_name
        """,
        [run_id],
    ).fetchall()
    return [
        CandidateScore(
            candidate_name=r[0],
            cover_image_sk=int(r[1]),
            objective_score=float(r[2] or 0),
            popularity_score=float(r[3] or 0),
            diversity_score=float(r[4] or 0),
            month_fit_score=float(r[5] or 0),
            cover_fit_score=float(r[6] or 0),
            redundancy_penalty=float(r[7] or 0),
            uncertainty_penalty=float(r[8] or 0),
        )
        for r in rows
    ]


def fetch_candidate_images(conn: duckdb.DuckDBPyConnection, run_id: str, candidate_name: str) -> list[MonthImage]:
    """Fetch the 13 month-image assignments with visual features and scores."""
    rows = conn.execute(
        f"""
        SELECT m.sequence_number, m.month_label, m.image_sk,
               d.source_image_id, d.title, d.description,
               m.month_fit_score, m.preference_score,
               v.brightness_score, v.contrast_score, v.saturation_score,
               v.dominant_color_json,
               c.cluster_id,
               p.broad_appeal_score, p.uncertainty_score
        FROM mart_calendar_candidate_month_image m
        JOIN dim_image d ON d.image_sk = m.image_sk
        LEFT JOIN feature_image_visual v ON v.image_sk = m.image_sk
        LEFT JOIN feature_image_cluster c
            ON c.image_sk = m.image_sk
            AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        LEFT JOIN mart_image_preference_score p
            ON p.image_sk = m.image_sk
            AND p.score_run_id = {LATEST_SCORE_RUN}
        WHERE m.candidate_run_id = ? AND m.candidate_name = ?
        ORDER BY m.sequence_number
        """,
        [run_id, candidate_name],
    ).fetchall()
    return [
        MonthImage(
            sequence_number=int(r[0]),
            month_label=r[1],
            image_sk=int(r[2]),
            source_image_id=r[3],
            title=r[4],
            description=r[5],
            month_fit_score=float(r[6] or 0),
            preference_score=float(r[7] or 0),
            brightness_score=float(r[8]) if r[8] is not None else None,
            contrast_score=float(r[9]) if r[9] is not None else None,
            saturation_score=float(r[10]) if r[10] is not None else None,
            dominant_color_json=r[11],
            cluster_id=int(r[12]) if r[12] is not None else None,
            broad_appeal_score=float(r[13]) if r[13] is not None else None,
            uncertainty_score=float(r[14]) if r[14] is not None else None,
        )
        for r in rows
    ]


def fetch_cluster_alternatives(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    candidate_name: str,
    image_sk: int,
    cluster_id: int,
    limit: int = 5,
) -> list[ClusterAlternative]:
    """Fetch top images in the same cluster that were NOT selected by this candidate."""
    # Get the set of selected image_sks for this candidate
    rows = conn.execute(
        f"""
        SELECT p.image_sk, d.source_image_id,
               p.posterior_mean, p.broad_appeal_score
        FROM mart_image_preference_score p
        JOIN dim_image d ON d.image_sk = p.image_sk
        JOIN feature_image_cluster c
            ON c.image_sk = p.image_sk
            AND c.cluster_type = 'visual'
            AND c.cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
        WHERE c.cluster_id = ?
          AND p.image_sk != ?
          AND p.image_sk NOT IN (
              SELECT image_sk FROM mart_calendar_candidate_month_image
              WHERE candidate_run_id = ? AND candidate_name = ?
          )
          AND p.score_run_id = {LATEST_SCORE_RUN}
        ORDER BY p.posterior_mean DESC
        LIMIT ?
        """,
        [cluster_id, image_sk, run_id, candidate_name, limit],
    ).fetchall()
    return [
        ClusterAlternative(
            image_sk=int(r[0]),
            source_image_id=r[1],
            preference_score=float(r[2] or 0),
            broad_appeal_score=float(r[3]) if r[3] is not None else None,
        )
        for r in rows
    ]


def fetch_preference_rank(conn: duckdb.DuckDBPyConnection, image_sk: int) -> int | None:
    """Fetch the popularity rank (1-based) for an image among all scored images."""
    row = conn.execute(
        f"""
        SELECT rank FROM (
            SELECT image_sk,
                   ROW_NUMBER() OVER (ORDER BY posterior_mean DESC) as rank
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
        ) ranked
        WHERE image_sk = ?
        """,
        [image_sk],
    ).fetchone()
    return int(row[0]) if row else None


def fetch_all_preference_ranks(
    conn: duckdb.DuckDBPyConnection,
) -> dict[int, int]:
    """Fetch popularity ranks for all scored images. Returns {image_sk: rank}."""
    rows = conn.execute(
        f"""
        SELECT image_sk,
               ROW_NUMBER() OVER (ORDER BY posterior_mean DESC) as rank
        FROM mart_image_preference_score
        WHERE score_run_id = {LATEST_SCORE_RUN}
        """
    ).fetchall()
    return {int(r[0]): int(r[1]) for r in rows}
