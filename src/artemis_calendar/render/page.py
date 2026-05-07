"""Monthly page and cover page composition."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from artemis_calendar.render.grid import render_calendar_grid
from artemis_calendar.render.layout import (
    DESC_REGION,
    GRID_REGION,
    IMAGE_REGION,
    PAGE_BG,
    PAGE_H,
    PAGE_W,
    TEXT_COLOR,
    TITLE_REGION,
)


def _center_crop_to_region(
    img: Image.Image,
    region: tuple[int, int, int, int],
) -> Image.Image:
    """Resize and center-crop an image to fill the target region exactly.

    If the source aspect ratio is extremely different (>3:1 or <1:3),
    uses letterbox (fit-within) instead to avoid aggressive cropping.
    """
    left, top, right, bottom = region
    target_w = right - left
    target_h = bottom - top

    src_w, src_h = img.size
    src_aspect = src_w / max(src_h, 1)

    # Letterbox fallback for extreme aspect ratios
    if src_aspect > 3.0 or src_aspect < 1 / 3.0:
        img.thumbnail((target_w, target_h), Image.LANCZOS)
        result = Image.new("RGB", (target_w, target_h), PAGE_BG)
        paste_x = (target_w - img.width) // 2
        paste_y = (target_h - img.height) // 2
        result.paste(img, (paste_x, paste_y))
        return result

    # Center-crop to fill
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    crop_x = (new_w - target_w) // 2
    crop_y = (new_h - target_h) // 2
    return img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))


def render_month_page(
    image_path: Path | str,
    year: int,
    month: int,
    sequence: int,
    label: str,
    fonts: dict[str, ImageFont.FreeTypeFont],
    title: str | None = None,
    description: str | None = None,
) -> Image.Image:
    """Render a complete monthly calendar page.

    Returns a 2550x3300 RGB image with the photo on top, month title,
    calendar grid, and optional description block.
    """
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
    draw = ImageDraw.Draw(page)

    # Place the photo in the image region
    photo = Image.open(image_path).convert("RGB")
    cropped = _center_crop_to_region(photo, IMAGE_REGION)
    page.paste(cropped, (IMAGE_REGION[0], IMAGE_REGION[1]))

    # Month title centered in title region
    title_x = (TITLE_REGION[0] + TITLE_REGION[2]) // 2
    title_y = (TITLE_REGION[1] + TITLE_REGION[3]) // 2
    draw.text((title_x, title_y), label, fill=TEXT_COLOR, font=fonts["month_title"], anchor="mm")

    # Calendar grid
    render_calendar_grid(draw, year, month, GRID_REGION, fonts)

    # Optional description block
    if title or description:
        _draw_description(draw, fonts, title, description)

    return page


def _draw_description(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.FreeTypeFont],
    title: str | None,
    description: str | None,
) -> None:
    """Draw the description block in the bottom-right region."""
    left, top, right, bottom = DESC_REGION
    max_width = right - left
    y = top

    if title:
        # Truncate title if too long
        truncated = title[:60] + "..." if len(title) > 60 else title
        draw.text((left, y), truncated, fill=TEXT_COLOR, font=fonts["description_title"])
        y += 30

    if description:
        # Word-wrap description to fit region width
        words = description[:250].split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = fonts["description_body"].getbbox(test)
            if bbox[2] - bbox[0] > max_width and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        for line in lines:
            if y + 24 > bottom:
                break
            draw.text((left, y), line, fill=TEXT_COLOR, font=fonts["description_body"])
            y += 24


def render_cover_page(
    image_path: Path | str,
    fonts: dict[str, ImageFont.FreeTypeFont],
    title: str = "FARTHER",
    subtitle: str = "2027 Calendar",
    date_range: str = "December 2026 \u2013 December 2027",
) -> Image.Image:
    """Render a full-bleed cover page with title overlay.

    Returns a 2550x3300 RGB image.
    """
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)

    # Full-bleed photo
    photo = Image.open(image_path).convert("RGB")
    cropped = _center_crop_to_region(photo, (0, 0, PAGE_W, PAGE_H))
    page.paste(cropped, (0, 0))

    draw = ImageDraw.Draw(page)

    # Semi-transparent dark overlay on bottom third
    overlay = Image.new("RGBA", (PAGE_W, PAGE_H // 3), (0, 0, 0, 140))
    page_rgba = page.convert("RGBA")
    page_rgba.paste(overlay, (0, PAGE_H * 2 // 3), overlay)
    page = page_rgba.convert("RGB")
    draw = ImageDraw.Draw(page)

    # Title text
    center_x = PAGE_W // 2
    text_base = PAGE_H * 2 // 3 + 80

    draw.text(
        (center_x, text_base),
        title,
        fill=(255, 255, 255),
        font=fonts["cover_title"],
        anchor="mt",
    )

    draw.text(
        (center_x, text_base + 170),
        subtitle,
        fill=(220, 220, 220),
        font=fonts["cover_subtitle"],
        anchor="mt",
    )

    draw.text(
        (center_x, text_base + 260),
        date_range,
        fill=(200, 200, 200),
        font=fonts["cover_date"],
        anchor="mt",
    )

    return page
