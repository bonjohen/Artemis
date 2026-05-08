"""Review package pipeline — orchestrates all review deliverables."""

from __future__ import annotations

from pathlib import Path

import duckdb

from artemis_calendar.config.settings import OUTPUT_ROOT, RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.render.layout import DPI
from artemis_calendar.review.comparison import render_comparison_page
from artemis_calendar.review.queries import (
    fetch_all_candidates,
    resolve_run_id,
)

logger = get_logger("artemis.review.pipeline")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"


def _thumb_path(guid: str) -> Path:
    """Resolve thumbnail path for a GUID."""
    return THUMB_DIR / f"{guid}.jpg"


def _get_cover_guid(conn: duckdb.DuckDBPyConnection, cover_image_sk: int) -> str:
    """Look up the source_image_id (GUID) for a cover image."""
    row = conn.execute(
        "SELECT source_image_id FROM dim_image WHERE image_sk = ?",
        [cover_image_sk],
    ).fetchone()
    if not row:
        raise ValueError(f"No image found for image_sk={cover_image_sk}")
    return row[0]


def generate_review_package(
    conn: duckdb.DuckDBPyConnection,
    run_id: str | None = None,
    winner: str = "method_b",
    skip_render: bool = False,
) -> Path:
    """Generate the full review package for a calendar optimization run.

    Args:
        conn: DuckDB connection.
        run_id: Optimization run ID (default: latest).
        winner: Candidate name to use for the export package.
        skip_render: If True, skip rendering full calendars.

    Returns:
        Path to the review output directory.
    """
    run_id = resolve_run_id(conn, run_id)
    logger.info(f"Generating review package for run {run_id}")

    # Output directory
    review_dir = OUTPUT_ROOT / "review" / run_id
    review_dir.mkdir(parents=True, exist_ok=True)

    # --- Fetch data ---
    candidates = fetch_all_candidates(conn, run_id)
    if not candidates:
        raise ValueError(f"No candidates found for run {run_id}")
    logger.info(f"Found {len(candidates)} candidates")

    # --- Deliverable 1: Candidate Comparison ---
    thumb_paths: dict[str, Path] = {}
    for cand in candidates:
        guid = _get_cover_guid(conn, cand.cover_image_sk)
        thumb_paths[cand.candidate_name] = _thumb_path(guid)

    comparison = render_comparison_page(candidates, thumb_paths)
    comparison.save(review_dir / "comparison.png", dpi=(DPI, DPI))
    comparison.save(review_dir / "comparison.pdf", resolution=DPI)
    logger.info("Rendered candidate comparison page")

    # --- Deliverable 2: Full Rendered Preview ---
    if not skip_render:
        from artemis_calendar.render.pipeline import render_calendar

        for cand in candidates:
            cal_dir = OUTPUT_ROOT / "calendars" / cand.candidate_name
            if (cal_dir / "calendar.pdf").exists():
                logger.info(f"Calendar already rendered for {cand.candidate_name}, skipping")
                continue
            try:
                render_calendar(conn, cand.candidate_name, run_id)
            except Exception as e:
                logger.warning(f"Could not render calendar for {cand.candidate_name}: {e}")

    # Collect all pages for combined PDF
    all_pages = [comparison]

    # Combine into review package PDF
    if len(all_pages) > 1:
        all_pages[0].save(
            review_dir / "review_package.pdf",
            save_all=True,
            append_images=all_pages[1:],
            resolution=DPI,
        )
    else:
        all_pages[0].save(review_dir / "review_package.pdf", resolution=DPI)
    logger.info(f"Review package saved to {review_dir}")

    return review_dir
