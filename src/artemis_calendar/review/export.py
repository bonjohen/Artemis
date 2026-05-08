"""Final export package assembly — copies winner's artifacts to a clean directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from artemis_calendar.config.settings import OUTPUT_ROOT
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.review.export")


def assemble_export(
    run_id: str,
    winner: str,
    review_dir: Path,
) -> Path:
    """Assemble the final export package for the winning candidate.

    Copies the winner's calendar PDF, contact sheet, selection report,
    comparison page, and validation page into a clean export directory.

    Args:
        run_id: Optimization run ID.
        winner: Winning candidate name (e.g. "method_b").
        review_dir: Path to the review output directory.

    Returns:
        Path to the export directory.
    """
    export_dir = OUTPUT_ROOT / "export" / run_id
    export_dir.mkdir(parents=True, exist_ok=True)

    # Calendar PDF from render output
    cal_pdf = OUTPUT_ROOT / "calendars" / winner / "calendar.pdf"
    if cal_pdf.exists():
        shutil.copy2(cal_pdf, export_dir / "calendar.pdf")
        logger.info(f"Copied calendar PDF for {winner}")
    else:
        logger.warning(f"Calendar PDF not found for {winner} at {cal_pdf}")

    # Review artifacts
    artifacts = [
        ("comparison.png", "comparison.png"),
        (f"{winner}_contact_sheet.png", "contact_sheet.png"),
        (f"{winner}_selection_report.pdf", "selection_report.pdf"),
        (f"{winner}_validation.png", "validation.png"),
        ("review_package.pdf", "review_package.pdf"),
    ]

    for src_name, dst_name in artifacts:
        src = review_dir / src_name
        if src.exists():
            shutil.copy2(src, export_dir / dst_name)
            logger.info(f"Copied {src_name} -> {dst_name}")
        else:
            logger.warning(f"Review artifact not found: {src}")

    logger.info(f"Export package assembled at {export_dir}")
    return export_dir
