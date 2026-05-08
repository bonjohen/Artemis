"""Selection report — multi-page rationale for a candidate's image choices."""

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
from artemis_calendar.review.queries import ClusterAlternative, MonthImage

# Layout constants
IMAGES_PER_PAGE = 3
BLOCK_HEIGHT = 950  # height per image block
THUMB_W = 600
THUMB_H = 400
ALT_THUMB_SIZE = 120  # cluster alternative thumbnail size

# Colors
LABEL_COLOR = (80, 80, 80)
ACCENT_COLOR = (50, 100, 170)
DIVIDER_COLOR = (200, 200, 200)

METHOD_DESCRIPTIONS: dict[str, str] = {
    "method_a": "Top Popularity (baseline)",
    "method_b": "Cluster-Limited Popularity",
    "method_c": "Top Per Cluster",
    "method_d": "Month-First Selection",
    "method_e": "MMR Greedy (multi-objective)",
}


def _load_report_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    return {
        "title": ImageFont.truetype(FONT_BOLD, 48),
        "subtitle": ImageFont.truetype(FONT_LIGHT, 24),
        "month": ImageFont.truetype(FONT_BOLD, 28),
        "label": ImageFont.truetype(FONT_REGULAR, 20),
        "value": ImageFont.truetype(FONT_BOLD, 20),
        "small": ImageFont.truetype(FONT_REGULAR, 16),
        "alt_label": ImageFont.truetype(FONT_REGULAR, 14),
    }


def _render_image_block(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.FreeTypeFont],
    img_data: MonthImage,
    rank: int | None,
    alternatives: list[ClusterAlternative],
    thumb_dir: Path,
    block_top: int,
) -> None:
    """Render a single image block within a report page."""
    # Thumbnail on the left
    thumb_path = thumb_dir / f"{img_data.source_image_id}.jpg"
    thumb_left = MARGIN
    if thumb_path.exists():
        try:
            thumb = Image.open(thumb_path)
            thumb.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
            page.paste(thumb, (thumb_left, block_top))
        except Exception:
            draw.rectangle(
                [thumb_left, block_top, thumb_left + THUMB_W, block_top + THUMB_H],
                outline=LABEL_COLOR,
            )
    else:
        draw.rectangle(
            [thumb_left, block_top, thumb_left + THUMB_W, block_top + THUMB_H],
            outline=LABEL_COLOR,
        )

    # Score details on the right
    detail_left = thumb_left + THUMB_W + 40
    detail_top = block_top

    # Month label
    draw.text((detail_left, detail_top), img_data.month_label, font=fonts["month"], fill=ACCENT_COLOR)
    detail_top += 40

    # Image ID
    guid = img_data.source_image_id or "unknown"
    draw.text((detail_left, detail_top), f"Image: {guid}", font=fonts["small"], fill=LABEL_COLOR)
    detail_top += 25

    # Score rows
    score_lines = [
        ("Preference Score", f"{img_data.preference_score:.4f}"),
        ("Preference Rank", f"#{rank}" if rank else "N/A"),
        ("Month Fit", f"{img_data.month_fit_score:.4f}"),
    ]
    if img_data.broad_appeal_score is not None:
        score_lines.append(("Broad Appeal", f"{img_data.broad_appeal_score:.4f}"))
    if img_data.uncertainty_score is not None:
        score_lines.append(("Uncertainty", f"{img_data.uncertainty_score:.4f}"))
    if img_data.cluster_id is not None:
        score_lines.append(("Visual Cluster", str(img_data.cluster_id)))
    if img_data.brightness_score is not None:
        score_lines.append(("Brightness", f"{img_data.brightness_score:.3f}"))
    if img_data.contrast_score is not None:
        score_lines.append(("Contrast", f"{img_data.contrast_score:.3f}"))

    for label_text, value_text in score_lines:
        draw.text((detail_left, detail_top), f"{label_text}:", font=fonts["label"], fill=LABEL_COLOR)
        draw.text((detail_left + 250, detail_top), value_text, font=fonts["value"], fill=TEXT_COLOR)
        detail_top += 28

    # Cluster alternatives row (below the thumbnail)
    alt_top = block_top + THUMB_H + 15
    if alternatives and img_data.cluster_id is not None:
        draw.text(
            (MARGIN, alt_top),
            f"Cluster {img_data.cluster_id} alternatives (not selected):",
            font=fonts["small"],
            fill=LABEL_COLOR,
        )
        alt_top += 22

        for alt_idx, alt in enumerate(alternatives[:5]):
            alt_left = MARGIN + alt_idx * (ALT_THUMB_SIZE + 15)
            alt_thumb_path = thumb_dir / f"{alt.source_image_id}.jpg"
            if alt_thumb_path.exists():
                try:
                    alt_img = Image.open(alt_thumb_path)
                    alt_img.thumbnail((ALT_THUMB_SIZE, ALT_THUMB_SIZE), Image.LANCZOS)
                    page.paste(alt_img, (alt_left, alt_top))
                except Exception:
                    draw.rectangle(
                        [alt_left, alt_top, alt_left + ALT_THUMB_SIZE, alt_top + ALT_THUMB_SIZE],
                        outline=LABEL_COLOR,
                    )
            else:
                draw.rectangle(
                    [alt_left, alt_top, alt_left + ALT_THUMB_SIZE, alt_top + ALT_THUMB_SIZE],
                    outline=LABEL_COLOR,
                )
            # Score label below alt thumbnail
            draw.text(
                (alt_left, alt_top + ALT_THUMB_SIZE + 2),
                f"{alt.preference_score:.3f}",
                font=fonts["alt_label"],
                fill=LABEL_COLOR,
            )

    # Divider line at bottom of block
    divider_y = block_top + BLOCK_HEIGHT - 10
    draw.line([(MARGIN, divider_y), (PAGE_W - MARGIN, divider_y)], fill=DIVIDER_COLOR, width=2)


def render_selection_report(
    candidate_name: str,
    objective_score: float,
    images: list[MonthImage],
    ranks: dict[int, int],
    alternatives: dict[int, list[ClusterAlternative]],
    thumb_dir: Path,
) -> list[Image.Image]:
    """Render the selection report as a list of page images.

    Args:
        candidate_name: e.g. "method_b".
        objective_score: Calendar-level objective score.
        images: 13 MonthImage objects, ordered by sequence_number.
        ranks: Mapping of image_sk to preference rank (1-based).
        alternatives: Mapping of image_sk to cluster alternatives.
        thumb_dir: Directory containing thumbnail JPGs.

    Returns:
        List of PIL Images (each 2550x3300 at 300 DPI).
    """
    fonts = _load_report_fonts()
    pages: list[Image.Image] = []

    for page_idx in range(0, len(images), IMAGES_PER_PAGE):
        page_images = images[page_idx : page_idx + IMAGES_PER_PAGE]
        page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
        draw = ImageDraw.Draw(page)

        # Page title (first page only has full title, subsequent pages have continuation)
        if page_idx == 0:
            friendly = candidate_name.replace("_", " ").title()
            desc = METHOD_DESCRIPTIONS.get(candidate_name, "")
            draw.text((MARGIN, 20), f"{friendly} — Selection Report", font=fonts["title"], fill=TEXT_COLOR)
            draw.text(
                (MARGIN, 75),
                f"{desc}  |  Objective: {objective_score:.3f}",
                font=fonts["subtitle"],
                fill=LABEL_COLOR,
            )
            content_top = 130
        else:
            page_num = page_idx // IMAGES_PER_PAGE + 1
            draw.text(
                (MARGIN, 20),
                f"{candidate_name.replace('_', ' ').title()} — Selection Report (p. {page_num})",
                font=fonts["title"],
                fill=TEXT_COLOR,
            )
            content_top = 90

        # Render image blocks
        for block_idx, img_data in enumerate(page_images):
            block_top = content_top + block_idx * BLOCK_HEIGHT
            rank = ranks.get(img_data.image_sk)
            alts = alternatives.get(img_data.image_sk, [])
            _render_image_block(page, draw, fonts, img_data, rank, alts, thumb_dir, block_top)

        pages.append(page)

    return pages
