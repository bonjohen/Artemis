"""Candidate comparison scorecard — a single page showing all candidates side-by-side."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from artemis_calendar.render.layout import (
    FONT_BOLD,
    FONT_LIGHT,
    FONT_REGULAR,
    MARGIN,
    PAGE_BG,
    PAGE_H,
    PAGE_W,
    TEXT_COLOR,
)
from artemis_calendar.review.queries import CandidateScore

# Layout constants for comparison page
TITLE_HEIGHT = 120
THUMB_HEIGHT = 340
THUMB_TOP = TITLE_HEIGHT + 20
SCORE_TOP = THUMB_TOP + THUMB_HEIGHT + 20

# Colors
HIGHLIGHT_BG = (220, 240, 220)  # Light green for best-in-row
HEADER_BG = (60, 60, 80)  # Dark header bar
HEADER_TEXT = (255, 255, 255)
ROW_ALT_BG = (245, 245, 250)  # Alternating row background
LABEL_COLOR = (80, 80, 80)

# Score labels and whether higher is better
SCORE_ROWS: list[tuple[str, str, bool]] = [
    ("Objective", "objective_score", True),
    ("Popularity", "popularity_score", True),
    ("Diversity", "diversity_score", True),
    ("Month Fit", "month_fit_score", True),
    ("Cover Fit", "cover_fit_score", True),
    ("Redundancy", "redundancy_penalty", False),  # lower is better
    ("Uncertainty", "uncertainty_penalty", False),  # lower is better
]


def _load_comparison_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    return {
        "title": ImageFont.truetype(FONT_BOLD, 56),
        "subtitle": ImageFont.truetype(FONT_LIGHT, 28),
        "method_name": ImageFont.truetype(FONT_BOLD, 28),
        "score_label": ImageFont.truetype(FONT_REGULAR, 24),
        "score_value": ImageFont.truetype(FONT_REGULAR, 24),
        "score_best": ImageFont.truetype(FONT_BOLD, 24),
        "rank_label": ImageFont.truetype(FONT_BOLD, 20),
    }


def _friendly_name(candidate_name: str) -> str:
    """Convert method_a to Method A."""
    parts = candidate_name.split("_")
    if len(parts) == 2:
        return f"{parts[0].capitalize()} {parts[1].upper()}"
    return candidate_name


METHOD_DESCRIPTIONS: dict[str, str] = {
    "method_a": "Top Popularity",
    "method_b": "Cluster-Limited",
    "method_c": "Per Cluster",
    "method_d": "Month-First",
    "method_e": "MMR Greedy",
}


def render_comparison_page(
    candidates: list[CandidateScore],
    thumb_paths: dict[str, Path],
) -> Image.Image:
    """Render a single comparison page showing all candidates side-by-side.

    Args:
        candidates: List of CandidateScore objects (one per method).
        thumb_paths: Mapping of candidate_name to cover thumbnail path.

    Returns:
        PIL Image of the comparison page (2550x3300 at 300 DPI).
    """
    fonts = _load_comparison_fonts()
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
    draw = ImageDraw.Draw(page)

    n = len(candidates)
    if n == 0:
        return page

    # --- Title ---
    draw.text(
        (MARGIN, 30),
        "Candidate Comparison",
        font=fonts["title"],
        fill=TEXT_COLOR,
    )
    draw.text(
        (MARGIN, 90),
        f"{n} selection methods compared",
        font=fonts["subtitle"],
        fill=LABEL_COLOR,
    )

    # --- Column layout ---
    usable_w = PAGE_W - 2 * MARGIN
    col_w = usable_w // n
    gutter = 20

    # --- Rank candidates by objective score ---
    ranked = sorted(candidates, key=lambda c: c.objective_score, reverse=True)
    rank_map = {c.candidate_name: i + 1 for i, c in enumerate(ranked)}

    # --- Find best values per score row ---
    best_per_row: dict[str, float] = {}
    for _label, attr, higher_better in SCORE_ROWS:
        values = [getattr(c, attr) for c in candidates]
        best_per_row[attr] = max(values) if higher_better else min(values)

    # --- Draw columns ---
    for col_idx, cand in enumerate(candidates):
        col_left = MARGIN + col_idx * col_w
        col_center = col_left + col_w // 2

        # Method name
        name = _friendly_name(cand.candidate_name)
        desc = METHOD_DESCRIPTIONS.get(cand.candidate_name, "")
        bbox = draw.textbbox((0, 0), name, font=fonts["method_name"])
        name_w = bbox[2] - bbox[0]
        draw.text(
            (col_center - name_w // 2, THUMB_TOP - 5),
            name,
            font=fonts["method_name"],
            fill=TEXT_COLOR,
        )

        # Description below name
        bbox_d = draw.textbbox((0, 0), desc, font=fonts["score_label"])
        desc_w = bbox_d[2] - bbox_d[0]
        draw.text(
            (col_center - desc_w // 2, THUMB_TOP + 30),
            desc,
            font=fonts["score_label"],
            fill=LABEL_COLOR,
        )

        # Cover thumbnail
        thumb_path = thumb_paths.get(cand.candidate_name)
        thumb_region_top = THUMB_TOP + 60
        thumb_w = col_w - gutter * 2
        thumb_h = THUMB_HEIGHT - 100
        if thumb_path and thumb_path.exists():
            try:
                thumb = Image.open(thumb_path)
                thumb.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                paste_x = col_center - thumb.width // 2
                page.paste(thumb, (paste_x, thumb_region_top))
            except Exception:
                # Draw placeholder
                draw.rectangle(
                    [col_left + gutter, thumb_region_top, col_left + col_w - gutter, thumb_region_top + thumb_h],
                    outline=LABEL_COLOR,
                )
        else:
            draw.rectangle(
                [col_left + gutter, thumb_region_top, col_left + col_w - gutter, thumb_region_top + thumb_h],
                outline=LABEL_COLOR,
            )

        # Rank badge
        rank = rank_map[cand.candidate_name]
        rank_text = f"#{rank}"
        bbox_r = draw.textbbox((0, 0), rank_text, font=fonts["rank_label"])
        rank_w = bbox_r[2] - bbox_r[0]
        draw.text(
            (col_center - rank_w // 2, thumb_region_top + thumb_h + 8),
            rank_text,
            font=fonts["rank_label"],
            fill=TEXT_COLOR,
        )

    # --- Score matrix ---
    row_height = 60
    label_col_w = 280

    # Header row
    header_y = SCORE_TOP
    draw.rectangle(
        [MARGIN, header_y, PAGE_W - MARGIN, header_y + row_height],
        fill=HEADER_BG,
    )
    draw.text(
        (MARGIN + 10, header_y + 15),
        "Metric",
        font=fonts["score_label"],
        fill=HEADER_TEXT,
    )
    for col_idx, cand in enumerate(candidates):
        col_left = MARGIN + label_col_w + col_idx * ((usable_w - label_col_w) // n)
        col_center = col_left + ((usable_w - label_col_w) // n) // 2
        name = _friendly_name(cand.candidate_name)
        bbox = draw.textbbox((0, 0), name, font=fonts["score_label"])
        name_w = bbox[2] - bbox[0]
        draw.text(
            (col_center - name_w // 2, header_y + 15),
            name,
            font=fonts["score_label"],
            fill=HEADER_TEXT,
        )

    # Score rows
    for row_idx, (label, attr, _higher_better) in enumerate(SCORE_ROWS):
        row_y = SCORE_TOP + (row_idx + 1) * row_height
        best_val = best_per_row[attr]

        # Alternating row background
        if row_idx % 2 == 0:
            draw.rectangle(
                [MARGIN, row_y, PAGE_W - MARGIN, row_y + row_height],
                fill=ROW_ALT_BG,
            )

        # Row label
        draw.text(
            (MARGIN + 10, row_y + 15),
            label,
            font=fonts["score_label"],
            fill=TEXT_COLOR,
        )

        # Values
        for col_idx, cand in enumerate(candidates):
            val = getattr(cand, attr)
            col_left = MARGIN + label_col_w + col_idx * ((usable_w - label_col_w) // n)
            cell_w = (usable_w - label_col_w) // n
            col_center = col_left + cell_w // 2

            is_best = abs(val - best_val) < 1e-9
            if is_best:
                draw.rectangle(
                    [col_left + 4, row_y + 2, col_left + cell_w - 4, row_y + row_height - 2],
                    fill=HIGHLIGHT_BG,
                )

            val_text = f"{val:.3f}"
            font = fonts["score_best"] if is_best else fonts["score_value"]
            bbox = draw.textbbox((0, 0), val_text, font=font)
            val_w = bbox[2] - bbox[0]
            draw.text(
                (col_center - val_w // 2, row_y + 15),
                val_text,
                font=font,
                fill=TEXT_COLOR,
            )

    # --- Bottom note ---
    note_y = SCORE_TOP + (len(SCORE_ROWS) + 1) * row_height + 30
    draw.text(
        (MARGIN, note_y),
        "Green highlight = best value for that metric. Redundancy and uncertainty: lower is better.",
        font=fonts["score_label"],
        fill=LABEL_COLOR,
    )

    return page
