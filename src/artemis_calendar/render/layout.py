"""Page layout constants and font loading for 8.5x11 portrait calendar pages."""

from __future__ import annotations

import platform

from PIL import ImageFont

from artemis_calendar.config import settings as cfg

# 300 DPI on 8.5 x 11 inch page
DPI = 300
PAGE_W = 2550  # 8.5 * 300
PAGE_H = 3300  # 11.0 * 300
MARGIN = 75  # 0.25 inch

# Image region: top half of page
IMAGE_LEFT = MARGIN
IMAGE_TOP = MARGIN
IMAGE_RIGHT = PAGE_W - MARGIN
IMAGE_BOTTOM = PAGE_H // 2
IMAGE_REGION = (IMAGE_LEFT, IMAGE_TOP, IMAGE_RIGHT, IMAGE_BOTTOM)

# Month title sits just below the image region
TITLE_TOP = IMAGE_BOTTOM + 30
TITLE_HEIGHT = 100
TITLE_REGION = (MARGIN, TITLE_TOP, PAGE_W - MARGIN, TITLE_TOP + TITLE_HEIGHT)

# Bottom half below title: calendar grid (left 75%) and description (right 25%)
BOTTOM_TOP = TITLE_TOP + TITLE_HEIGHT + 20
BOTTOM_BOTTOM = PAGE_H - MARGIN

GRID_LEFT = MARGIN
GRID_RIGHT = MARGIN + int((PAGE_W - 2 * MARGIN) * 0.75)
GRID_REGION = (GRID_LEFT, BOTTOM_TOP, GRID_RIGHT, BOTTOM_BOTTOM)

DESC_LEFT = GRID_RIGHT + 30
DESC_RIGHT = PAGE_W - MARGIN
DESC_TOP = BOTTOM_BOTTOM - 400  # description block anchored to bottom-right
DESC_REGION = (DESC_LEFT, DESC_TOP, DESC_RIGHT, BOTTOM_BOTTOM)


# Font paths — env-var override > platform defaults
def _default_fonts() -> tuple[str, str, str]:
    if platform.system() == "Windows":
        return ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeuil.ttf")
    import shutil

    if shutil.which("fc-list") and platform.system() == "Linux":
        return (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
        )
    return ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf", "/Library/Fonts/Arial.ttf")


_reg, _bold, _light = _default_fonts()
FONT_REGULAR = cfg.FONT_REGULAR or _reg
FONT_BOLD = cfg.FONT_BOLD or _bold
FONT_LIGHT = cfg.FONT_LIGHT or _light

# Background color
PAGE_BG = (255, 255, 255)
TEXT_COLOR = (30, 30, 30)
GRID_LINE_COLOR = (200, 200, 200)
DAY_HEADER_COLOR = (80, 80, 80)
WEEKEND_COLOR = (180, 60, 60)


def load_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    """Load fonts at sizes needed for calendar rendering."""
    return {
        "month_title": ImageFont.truetype(FONT_BOLD, 72),
        "day_header": ImageFont.truetype(FONT_BOLD, 28),
        "day_number": ImageFont.truetype(FONT_REGULAR, 32),
        "description_title": ImageFont.truetype(FONT_BOLD, 20),
        "description_body": ImageFont.truetype(FONT_REGULAR, 18),
        "cover_title": ImageFont.truetype(FONT_BOLD, 140),
        "cover_subtitle": ImageFont.truetype(FONT_LIGHT, 60),
        "cover_date": ImageFont.truetype(FONT_REGULAR, 40),
    }
