"""Layout validation diagnostic page — flags potential issues in a candidate calendar."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from artemis_calendar.render.layout import (
    FONT_BOLD,
    FONT_REGULAR,
    IMAGE_REGION,
    MARGIN,
    PAGE_BG,
    PAGE_H,
    PAGE_W,
    TEXT_COLOR,
)
from artemis_calendar.review.queries import MonthImage

# Layout
TITLE_HEIGHT = 100
PANEL_PAD = 30
PANEL_W = (PAGE_W - 2 * MARGIN - PANEL_PAD) // 2
PANEL_H = (PAGE_H - TITLE_HEIGHT - 2 * MARGIN - PANEL_PAD) // 2

# Colors
LABEL_COLOR = (80, 80, 80)
GOOD_COLOR = (50, 150, 50)
WARN_COLOR = (200, 150, 30)
BAD_COLOR = (200, 50, 50)
PANEL_BG = (248, 248, 252)
PANEL_BORDER = (200, 200, 210)

# Thresholds
CROP_WARN_THRESHOLD = 0.30  # flag if >30% of image area is cropped away
BRIGHTNESS_SIMILARITY_THRESHOLD = 0.05  # consecutive months with similar brightness

METHOD_DESCRIPTIONS: dict[str, str] = {
    "method_a": "Top Popularity",
    "method_b": "Cluster-Limited",
    "method_c": "Per Cluster",
    "method_d": "Month-First",
    "method_e": "MMR Greedy",
}


def _load_validation_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    return {
        "title": ImageFont.truetype(FONT_BOLD, 48),
        "panel_title": ImageFont.truetype(FONT_BOLD, 28),
        "label": ImageFont.truetype(FONT_REGULAR, 18),
        "value": ImageFont.truetype(FONT_BOLD, 18),
        "small": ImageFont.truetype(FONT_REGULAR, 15),
    }


def _compute_crop_fraction(img_w: int, img_h: int) -> float:
    """Compute what fraction of the source image area is lost to center-cropping
    when fitting into the IMAGE_REGION."""
    left, top, right, bottom = IMAGE_REGION
    target_w = right - left
    target_h = bottom - top

    src_aspect = img_w / max(img_h, 1)
    if src_aspect > 3.0 or src_aspect < 1 / 3.0:
        return 0.0  # letterbox mode, no cropping

    scale = max(target_w / img_w, target_h / img_h)
    scaled_w = int(img_w * scale)
    scaled_h = int(img_h * scale)
    crop_area = scaled_w * scaled_h - target_w * target_h
    return crop_area / (scaled_w * scaled_h)


def _draw_panel_bg(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    """Draw panel background with border."""
    draw.rectangle([x, y, x + w, y + h], fill=PANEL_BG, outline=PANEL_BORDER, width=2)


def _parse_dominant_color(json_str: str | None) -> tuple[int, int, int] | None:
    """Parse dominant color from JSON string."""
    if not json_str:
        return None
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return (int(data.get("r", 128)), int(data.get("g", 128)), int(data.get("b", 128)))
        if isinstance(data, list) and len(data) >= 3:
            # Could be a list of colors; take the first one
            first = data[0]
            if isinstance(first, dict):
                return (int(first.get("r", 128)), int(first.get("g", 128)), int(first.get("b", 128)))
            if isinstance(first, (list, tuple)) and len(first) >= 3:
                return (int(first[0]), int(first[1]), int(first[2]))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def render_validation_page(
    candidate_name: str,
    images: list[MonthImage],
    thumb_dir: Path,
) -> Image.Image:
    """Render a layout validation diagnostic page with four panels.

    Panels:
        1. Aspect ratio / crop flags (top-left)
        2. Brightness distribution across months (top-right)
        3. Color palette / dominant colors (bottom-left)
        4. Cluster overlap analysis (bottom-right)

    Args:
        candidate_name: e.g. "method_b".
        images: 13 MonthImage objects.
        thumb_dir: Directory containing thumbnail JPGs.

    Returns:
        PIL Image (2550x3300 at 300 DPI).
    """
    fonts = _load_validation_fonts()
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
    draw = ImageDraw.Draw(page)

    # --- Title ---
    friendly = candidate_name.replace("_", " ").title()
    draw.text(
        (MARGIN, 20),
        f"{friendly} — Layout Validation",
        font=fonts["title"],
        fill=TEXT_COLOR,
    )

    # Panel positions
    top_y = TITLE_HEIGHT + 20
    left_x = MARGIN
    right_x = MARGIN + PANEL_W + PANEL_PAD
    bottom_y = top_y + PANEL_H + PANEL_PAD

    # === Panel 1: Aspect Ratio / Crop Analysis (top-left) ===
    _draw_panel_bg(draw, left_x, top_y, PANEL_W, PANEL_H)
    draw.text((left_x + 15, top_y + 10), "Aspect Ratio & Crop Analysis", font=fonts["panel_title"], fill=TEXT_COLOR)

    row_y = top_y + 50
    issue_count = 0
    for img in images:
        thumb_path = thumb_dir / f"{img.source_image_id}.jpg"
        if thumb_path.exists():
            try:
                thumb = Image.open(thumb_path)
                w, h = thumb.size
                thumb.close()
                crop_frac = _compute_crop_fraction(w, h)
                aspect_str = f"{w}x{h}"
                crop_str = f"{crop_frac:.0%} crop"

                if crop_frac > CROP_WARN_THRESHOLD:
                    color = BAD_COLOR
                    flag = " !!!"
                    issue_count += 1
                else:
                    color = GOOD_COLOR
                    flag = ""

                month_short = img.month_label[:3]
                line = f"{month_short}: {aspect_str}  ({crop_str}){flag}"
                draw.text((left_x + 15, row_y), line, font=fonts["label"], fill=color)
                row_y += 24
            except Exception:
                draw.text((left_x + 15, row_y), f"{img.month_label[:3]}: error", font=fonts["label"], fill=BAD_COLOR)
                row_y += 24
        else:
            draw.text(
                (left_x + 15, row_y),
                f"{img.month_label[:3]}: no thumbnail",
                font=fonts["label"],
                fill=WARN_COLOR,
            )
            row_y += 24

    summary_color = GOOD_COLOR if issue_count == 0 else BAD_COLOR
    draw.text(
        (left_x + 15, row_y + 10),
        f"{issue_count} image(s) with >30% crop loss",
        font=fonts["value"],
        fill=summary_color,
    )

    # === Panel 2: Brightness Distribution (top-right) ===
    _draw_panel_bg(draw, right_x, top_y, PANEL_W, PANEL_H)
    draw.text((right_x + 15, top_y + 10), "Brightness Distribution", font=fonts["panel_title"], fill=TEXT_COLOR)

    bar_top = top_y + 60
    bar_height = 50
    bar_max_width = PANEL_W - 60
    brightness_warnings = 0

    for idx, img in enumerate(images):
        y = bar_top + idx * (bar_height + 8)
        b = img.brightness_score if img.brightness_score is not None else 0.5

        # Draw brightness bar
        bar_width = int(b * bar_max_width)
        gray = int(b * 255)
        bar_color = (gray, gray, gray)
        draw.rectangle([right_x + 15, y, right_x + 15 + bar_width, y + bar_height], fill=bar_color)
        draw.rectangle(
            [right_x + 15, y, right_x + 15 + bar_max_width, y + bar_height],
            outline=PANEL_BORDER,
        )

        # Month label
        month_short = img.month_label[:3]
        text_color = TEXT_COLOR if gray < 180 else (50, 50, 50)
        draw.text((right_x + 20, y + 12), f"{month_short} ({b:.2f})", font=fonts["small"], fill=text_color)

        # Check for consecutive similar brightness
        if idx > 0:
            prev_b = images[idx - 1].brightness_score or 0.5
            if abs(b - prev_b) < BRIGHTNESS_SIMILARITY_THRESHOLD:
                brightness_warnings += 1
                draw.text(
                    (right_x + 15 + bar_max_width + 5, y + 12),
                    "~",
                    font=fonts["value"],
                    fill=WARN_COLOR,
                )

    summary_y = bar_top + 13 * (bar_height + 8) + 5
    if brightness_warnings > 0:
        draw.text(
            (right_x + 15, summary_y),
            f"{brightness_warnings} consecutive pair(s) with similar brightness",
            font=fonts["label"],
            fill=WARN_COLOR,
        )
    else:
        draw.text(
            (right_x + 15, summary_y),
            "Good brightness variation across months",
            font=fonts["label"],
            fill=GOOD_COLOR,
        )

    # === Panel 3: Color Palette (bottom-left) ===
    _draw_panel_bg(draw, left_x, bottom_y, PANEL_W, PANEL_H)
    draw.text((left_x + 15, bottom_y + 10), "Dominant Color Palette", font=fonts["panel_title"], fill=TEXT_COLOR)

    swatch_top = bottom_y + 55
    swatch_size = 70
    swatch_gap = 10
    swatches_per_row = (PANEL_W - 30) // (swatch_size + swatch_gap)

    for idx, img in enumerate(images):
        col = idx % swatches_per_row
        row = idx // swatches_per_row
        sx = left_x + 15 + col * (swatch_size + swatch_gap)
        sy = swatch_top + row * (swatch_size + 35)

        color = _parse_dominant_color(img.dominant_color_json)
        if color:
            draw.rectangle([sx, sy, sx + swatch_size, sy + swatch_size], fill=color, outline=PANEL_BORDER)
        else:
            draw.rectangle([sx, sy, sx + swatch_size, sy + swatch_size], fill=(200, 200, 200), outline=PANEL_BORDER)
            draw.text((sx + 10, sy + 25), "?", font=fonts["value"], fill=LABEL_COLOR)

        month_short = img.month_label[:3]
        draw.text((sx, sy + swatch_size + 3), month_short, font=fonts["small"], fill=LABEL_COLOR)

    # === Panel 4: Cluster Overlap (bottom-right) ===
    _draw_panel_bg(draw, right_x, bottom_y, PANEL_W, PANEL_H)
    draw.text((right_x + 15, bottom_y + 10), "Cluster Overlap Analysis", font=fonts["panel_title"], fill=TEXT_COLOR)

    # Count cluster usage
    cluster_counts: dict[int, list[str]] = {}
    for img in images:
        if img.cluster_id is not None:
            cluster_counts.setdefault(img.cluster_id, []).append(img.month_label[:3])

    row_y = bottom_y + 55
    overlap_issues = 0
    for cluster_id in sorted(cluster_counts.keys()):
        months = cluster_counts[cluster_id]
        count = len(months)
        months_str = ", ".join(months)

        if count >= 3:
            color = BAD_COLOR
            flag = " (over-represented)"
            overlap_issues += 1
        elif count == 2:
            color = WARN_COLOR
            flag = ""
        else:
            color = GOOD_COLOR
            flag = ""

        line = f"Cluster {cluster_id}: {count} image(s) [{months_str}]{flag}"
        draw.text((right_x + 15, row_y), line, font=fonts["label"], fill=color)
        row_y += 26

    # Summary
    distinct = len(cluster_counts)
    total = len([img for img in images if img.cluster_id is not None])
    summary_y = row_y + 15
    draw.text(
        (right_x + 15, summary_y),
        f"{distinct} distinct clusters from {total} images",
        font=fonts["value"],
        fill=TEXT_COLOR,
    )
    if overlap_issues > 0:
        draw.text(
            (right_x + 15, summary_y + 28),
            f"{overlap_issues} cluster(s) with 3+ images — consider swaps",
            font=fonts["label"],
            fill=BAD_COLOR,
        )
    else:
        draw.text(
            (right_x + 15, summary_y + 28),
            "No over-represented clusters",
            font=fonts["label"],
            fill=GOOD_COLOR,
        )

    return page
