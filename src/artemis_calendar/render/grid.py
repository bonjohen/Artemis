"""Calendar grid rendering for monthly pages."""

from __future__ import annotations

import calendar

from PIL import ImageDraw, ImageFont

from artemis_calendar.render.layout import DAY_HEADER_COLOR, GRID_LINE_COLOR, TEXT_COLOR, WEEKEND_COLOR

# Day-of-week headers (Sunday start)
DAY_HEADERS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def render_calendar_grid(
    draw: ImageDraw.ImageDraw,
    year: int,
    month: int,
    region: tuple[int, int, int, int],
    fonts: dict[str, ImageFont.FreeTypeFont],
) -> None:
    """Draw a monthly calendar grid into the specified region.

    Uses Sunday as the first day of the week. The region tuple is
    (left, top, right, bottom) in pixel coordinates.
    """
    left, top, right, bottom = region
    width = right - left
    height = bottom - top

    col_w = width // 7
    header_h = 50
    day_font = fonts["day_number"]
    header_font = fonts["day_header"]

    # Draw day-of-week headers
    for i, label in enumerate(DAY_HEADERS):
        x = left + i * col_w + col_w // 2
        y = top + header_h // 2
        color = WEEKEND_COLOR if i in (0, 6) else DAY_HEADER_COLOR
        draw.text((x, y), label, fill=color, font=header_font, anchor="mm")

    # Separator line below headers
    line_y = top + header_h
    draw.line([(left, line_y), (right, line_y)], fill=GRID_LINE_COLOR, width=2)

    # Get weeks for this month (Sunday = 6 in calendar module, so use setfirstweekday)
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    weeks = cal.monthdayscalendar(year, month)

    # Row height for day cells
    grid_h = height - header_h - 10
    row_h = grid_h // max(len(weeks), 1)

    for week_idx, week in enumerate(weeks):
        row_top = line_y + 10 + week_idx * row_h

        # Draw horizontal grid line between rows
        if week_idx > 0:
            draw.line([(left, row_top), (right, row_top)], fill=GRID_LINE_COLOR, width=1)

        for day_idx, day in enumerate(week):
            if day == 0:
                continue

            x = left + day_idx * col_w + col_w // 2
            y = row_top + row_h // 2
            color = WEEKEND_COLOR if day_idx in (0, 6) else TEXT_COLOR
            draw.text((x, y), str(day), fill=color, font=day_font, anchor="mm")

    # Draw vertical grid lines
    for i in range(1, 7):
        x = left + i * col_w
        draw.line([(x, top), (x, bottom)], fill=GRID_LINE_COLOR, width=1)
