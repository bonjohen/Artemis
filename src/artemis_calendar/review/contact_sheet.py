"""Contact sheet — a single page showing all 13 images in a grid for one candidate."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from artemis_calendar.render.layout import (
    FONT_BOLD,
    FONT_REGULAR,
    MARGIN,
    PAGE_BG,
    PAGE_H,
    PAGE_W,
    TEXT_COLOR,
)
from artemis_calendar.review.queries import MonthImage

# Grid layout: 4 columns x 4 rows, 13 cells used
COLS = 4
ROWS = 4
TITLE_HEIGHT = 100
CELL_PAD = 15
LABEL_HEIGHT = 80  # space for text below each thumbnail

# Colors
LABEL_COLOR = (80, 80, 80)
ACCENT_COLOR = (50, 100, 170)

METHOD_DESCRIPTIONS: dict[str, str] = {
    "method_a": "Top Popularity (baseline)",
    "method_b": "Cluster-Limited Popularity",
    "method_c": "Top Per Cluster",
    "method_d": "Month-First Selection",
    "method_e": "MMR Greedy (multi-objective)",
}


def _load_contact_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    return {
        "title": ImageFont.truetype(FONT_BOLD, 48),
        "subtitle": ImageFont.truetype(FONT_REGULAR, 24),
        "month": ImageFont.truetype(FONT_BOLD, 20),
        "detail": ImageFont.truetype(FONT_REGULAR, 16),
    }


def render_contact_sheet(
    candidate_name: str,
    objective_score: float,
    images: list[MonthImage],
    thumb_dir: Path,
    ranks: dict[int, int],
) -> Image.Image:
    """Render a contact sheet with all 13 month images in a 4x4 grid.

    Args:
        candidate_name: e.g. "method_b".
        objective_score: Calendar-level objective score.
        images: 13 MonthImage objects, ordered by sequence_number.
        thumb_dir: Directory containing thumbnail JPGs.
        ranks: Mapping of image_sk to preference rank (1-based).

    Returns:
        PIL Image (2550x3300 at 300 DPI).
    """
    fonts = _load_contact_fonts()
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
    draw = ImageDraw.Draw(page)

    # --- Title ---
    friendly = candidate_name.replace("_", " ").title()
    desc = METHOD_DESCRIPTIONS.get(candidate_name, "")
    draw.text((MARGIN, 20), f"{friendly} — Contact Sheet", font=fonts["title"], fill=TEXT_COLOR)
    draw.text(
        (MARGIN, 75),
        f"{desc}  |  Objective: {objective_score:.3f}",
        font=fonts["subtitle"],
        fill=LABEL_COLOR,
    )

    # --- Grid geometry ---
    grid_top = TITLE_HEIGHT + 20
    usable_w = PAGE_W - 2 * MARGIN
    usable_h = PAGE_H - grid_top - MARGIN
    cell_w = (usable_w - (COLS - 1) * CELL_PAD) // COLS
    cell_h = (usable_h - (ROWS - 1) * CELL_PAD) // ROWS
    thumb_h = cell_h - LABEL_HEIGHT

    for idx, img_data in enumerate(images):
        col = idx % COLS
        row = idx // COLS
        x = MARGIN + col * (cell_w + CELL_PAD)
        y = grid_top + row * (cell_h + CELL_PAD)

        # Load and resize thumbnail
        thumb_path = thumb_dir / f"{img_data.source_image_id}.jpg"
        if thumb_path.exists():
            try:
                thumb = Image.open(thumb_path)
                # Center-crop to fill cell
                scale = max(cell_w / thumb.width, thumb_h / thumb.height)
                new_w = int(thumb.width * scale)
                new_h = int(thumb.height * scale)
                thumb = thumb.resize((new_w, new_h), Image.LANCZOS)
                crop_x = (new_w - cell_w) // 2
                crop_y = (new_h - thumb_h) // 2
                thumb = thumb.crop((crop_x, crop_y, crop_x + cell_w, crop_y + thumb_h))
                page.paste(thumb, (x, y))
            except Exception:
                draw.rectangle([x, y, x + cell_w, y + thumb_h], outline=LABEL_COLOR)
        else:
            draw.rectangle([x, y, x + cell_w, y + thumb_h], outline=LABEL_COLOR)

        # Sequence badge (top-left corner)
        badge_text = f"{img_data.sequence_number}"
        badge_bbox = draw.textbbox((0, 0), badge_text, font=fonts["month"])
        badge_w = badge_bbox[2] - badge_bbox[0] + 12
        badge_h = badge_bbox[3] - badge_bbox[1] + 8
        draw.rectangle([x, y, x + badge_w, y + badge_h], fill=ACCENT_COLOR)
        draw.text((x + 6, y + 2), badge_text, font=fonts["month"], fill=(255, 255, 255))

        # Text labels below thumbnail
        label_y = y + thumb_h + 4
        draw.text((x, label_y), img_data.month_label, font=fonts["month"], fill=TEXT_COLOR)

        guid_short = img_data.source_image_id[:12] if img_data.source_image_id else "?"
        rank = ranks.get(img_data.image_sk)
        rank_str = f"#{rank}" if rank else "?"
        detail_line = f"{guid_short}  Rank {rank_str}"
        draw.text((x, label_y + 22), detail_line, font=fonts["detail"], fill=LABEL_COLOR)

        score_line = f"Pref: {img_data.preference_score:.3f}  Fit: {img_data.month_fit_score:.3f}"
        draw.text((x, label_y + 40), score_line, font=fonts["detail"], fill=LABEL_COLOR)

        if img_data.cluster_id is not None:
            cluster_line = f"Cluster: {img_data.cluster_id}"
            draw.text((x, label_y + 58), cluster_line, font=fonts["detail"], fill=LABEL_COLOR)

    return page
