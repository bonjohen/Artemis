"""Calendar rendering pipeline — orchestrates download, render, and PDF assembly."""

from __future__ import annotations

from pathlib import Path

import duckdb
from PIL import Image

from artemis_calendar.config.settings import OUTPUT_ROOT, RAW_ROOT
from artemis_calendar.extract.images import download_candidate_images
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.render.layout import DPI, load_fonts
from artemis_calendar.render.page import render_cover_page, render_month_page

logger = get_logger("artemis.render.pipeline")

LARGE_DIR = RAW_ROOT / "images" / "large"


def render_calendar(
    conn: duckdb.DuckDBPyConnection,
    candidate_name: str,
    run_id: str | None = None,
) -> Path:
    """Render a complete calendar for the specified candidate.

    Downloads full-resolution images if needed, renders cover + 13 monthly
    pages as PNG and individual PDF, then combines into a single PDF.

    Returns the output directory path.
    """
    # Resolve run_id
    if run_id is None:
        row = conn.execute(
            "SELECT candidate_run_id FROM mart_calendar_candidate ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            raise ValueError("No calendar candidates found in warehouse")
        run_id = row[0]

    # Verify candidate exists
    candidate = conn.execute(
        "SELECT cover_image_sk, objective_score FROM mart_calendar_candidate "
        "WHERE candidate_name = ? AND candidate_run_id = ?",
        [candidate_name, run_id],
    ).fetchone()
    if not candidate:
        raise ValueError(f"Candidate '{candidate_name}' not found for run {run_id}")

    cover_image_sk = candidate[0]
    logger.info(f"Rendering calendar for {candidate_name} (run {run_id}, cover_sk={cover_image_sk})")

    # Get month-image assignments with image metadata
    assignments = conn.execute(
        """
        SELECT m.sequence_number, m.month_label, m.image_sk,
               d.source_image_id, d.title, d.description
        FROM mart_calendar_candidate_month_image m
        JOIN dim_image d ON d.image_sk = m.image_sk
        WHERE m.candidate_name = ? AND m.candidate_run_id = ?
        ORDER BY m.sequence_number
        """,
        [candidate_name, run_id],
    ).fetchall()

    if len(assignments) != 13:
        raise ValueError(f"Expected 13 month assignments, got {len(assignments)}")

    # Download full-resolution images
    download_candidate_images(conn, candidate_name, run_id)

    # Prepare output directory
    out_dir = OUTPUT_ROOT / "calendars" / candidate_name
    out_dir.mkdir(parents=True, exist_ok=True)

    fonts = load_fonts()

    # Parse month assignments
    pages: list[Image.Image] = []
    cover_guid = None

    for seq, label, image_sk, guid, title, description in assignments:
        if image_sk == cover_image_sk:
            cover_guid = guid

        # Parse year and month from label (e.g. "December 2026")
        parts = label.split()
        month_name = parts[0]
        year = int(parts[1])
        month_num = _month_name_to_num(month_name)

        image_path = _resolve_image_path(guid)

        # Render monthly page
        page = render_month_page(
            image_path,
            year,
            month_num,
            seq,
            label,
            fonts,
            title=title,
            description=description,
        )

        # Save individual PNG and PDF
        page_name = f"{seq:02d}_{month_name.lower()}_{year}"
        page.save(out_dir / f"{page_name}.png", dpi=(DPI, DPI))
        page.save(out_dir / f"{page_name}.pdf", resolution=DPI)
        pages.append(page)

        logger.info(f"Rendered page {seq}/13: {label}")

    # Render cover page
    if cover_guid is None:
        # Fallback: use the first image
        cover_guid = assignments[0][3]

    cover_path = _resolve_image_path(cover_guid)
    cover = render_cover_page(cover_path, fonts)
    cover.save(out_dir / "cover.png", dpi=(DPI, DPI))
    cover.save(out_dir / "cover.pdf", resolution=DPI)
    logger.info("Rendered cover page")

    # Combine into single PDF: cover + 13 monthly pages
    all_pages = [cover] + pages
    all_pages[0].save(
        out_dir / "calendar.pdf",
        save_all=True,
        append_images=all_pages[1:],
        resolution=DPI,
    )
    logger.info(f"Combined PDF saved to {out_dir / 'calendar.pdf'} ({len(all_pages)} pages)")

    return out_dir


def _month_name_to_num(name: str) -> int:
    """Convert month name to number (January=1, December=12)."""
    months = {
        "January": 1,
        "February": 2,
        "March": 3,
        "April": 4,
        "May": 5,
        "June": 6,
        "July": 7,
        "August": 8,
        "September": 9,
        "October": 10,
        "November": 11,
        "December": 12,
    }
    return months[name]


def _resolve_image_path(guid: str) -> Path:
    """Find the image file on disk — prefer full-res, fall back to thumbnail."""
    full = LARGE_DIR / f"{guid}.JPG"
    if full.exists():
        return full

    thumb = RAW_ROOT / "images" / "thumbs" / f"{guid}.jpg"
    if thumb.exists():
        logger.warning(f"Full-res image not found for {guid}, using thumbnail")
        return thumb

    raise FileNotFoundError(f"No image found for GUID {guid}")
