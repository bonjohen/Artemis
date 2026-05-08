"""Review package pipeline — orchestrates all review deliverables."""

from __future__ import annotations

from pathlib import Path

import duckdb
from PIL import Image

from artemis_calendar.config.settings import OUTPUT_ROOT, RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.render.layout import DPI
from artemis_calendar.review.comparison import render_comparison_page
from artemis_calendar.review.contact_sheet import render_contact_sheet
from artemis_calendar.review.export import assemble_export
from artemis_calendar.review.queries import (
    fetch_all_candidates,
    fetch_all_preference_ranks,
    fetch_candidate_images,
    fetch_cluster_alternatives,
    resolve_run_id,
)
from artemis_calendar.review.selection_report import render_selection_report
from artemis_calendar.review.validation import render_validation_page

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

    # --- Fetch shared data ---
    candidates = fetch_all_candidates(conn, run_id)
    if not candidates:
        raise ValueError(f"No candidates found for run {run_id}")
    logger.info(f"Found {len(candidates)} candidates")

    ranks = fetch_all_preference_ranks(conn)

    # Build a lookup of candidate_name -> objective_score
    score_by_name = {c.candidate_name: c.objective_score for c in candidates}

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
    all_pages: list[Image.Image] = [comparison]

    # --- Deliverables 3, 4, 5: Contact Sheet + Selection Report + Validation per candidate ---
    for cand in candidates:
        images = fetch_candidate_images(conn, run_id, cand.candidate_name)
        if not images:
            logger.warning(f"No images found for {cand.candidate_name}, skipping")
            continue

        # Contact sheet
        contact = render_contact_sheet(
            cand.candidate_name,
            score_by_name.get(cand.candidate_name, 0.0),
            images,
            THUMB_DIR,
            ranks,
        )
        contact.save(review_dir / f"{cand.candidate_name}_contact_sheet.png", dpi=(DPI, DPI))
        all_pages.append(contact)
        logger.info(f"Rendered contact sheet for {cand.candidate_name}")

        # Selection report — fetch cluster alternatives for each image
        alts: dict[int, list] = {}
        for img in images:
            if img.cluster_id is not None:
                alts[img.image_sk] = fetch_cluster_alternatives(
                    conn, run_id, cand.candidate_name, img.image_sk, img.cluster_id
                )

        report_pages = render_selection_report(
            cand.candidate_name,
            score_by_name.get(cand.candidate_name, 0.0),
            images,
            ranks,
            alts,
            THUMB_DIR,
        )
        if report_pages:
            report_pages[0].save(
                review_dir / f"{cand.candidate_name}_selection_report_p1.png",
                dpi=(DPI, DPI),
            )
            all_pages.extend(report_pages)

            if len(report_pages) > 1:
                report_pages[0].save(
                    review_dir / f"{cand.candidate_name}_selection_report.pdf",
                    save_all=True,
                    append_images=report_pages[1:],
                    resolution=DPI,
                )
            else:
                report_pages[0].save(
                    review_dir / f"{cand.candidate_name}_selection_report.pdf",
                    resolution=DPI,
                )
        logger.info(f"Rendered selection report for {cand.candidate_name} ({len(report_pages)} pages)")

        # Validation page
        validation = render_validation_page(cand.candidate_name, images, THUMB_DIR)
        validation.save(review_dir / f"{cand.candidate_name}_validation.png", dpi=(DPI, DPI))
        all_pages.append(validation)
        logger.info(f"Rendered validation page for {cand.candidate_name}")

    # --- Combine into review package PDF ---
    if len(all_pages) > 1:
        all_pages[0].save(
            review_dir / "review_package.pdf",
            save_all=True,
            append_images=all_pages[1:],
            resolution=DPI,
        )
    else:
        all_pages[0].save(review_dir / "review_package.pdf", resolution=DPI)
    logger.info(f"Review package saved to {review_dir} ({len(all_pages)} pages)")

    # --- Deliverable 6: Export Package ---
    export_dir = assemble_export(run_id, winner, review_dir)
    logger.info(f"Export package at {export_dir}")

    return review_dir
