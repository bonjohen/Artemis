"""Month suitability scoring for calendar image assignment."""

from __future__ import annotations

import json

import numpy as np

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.optimize.month_fit")

# 13-month calendar: December 2026 through December 2027
CALENDAR_MONTHS = [
    {"sequence": 1, "year": 2026, "month": 12, "label": "December 2026"},
    {"sequence": 2, "year": 2027, "month": 1, "label": "January 2027"},
    {"sequence": 3, "year": 2027, "month": 2, "label": "February 2027"},
    {"sequence": 4, "year": 2027, "month": 3, "label": "March 2027"},
    {"sequence": 5, "year": 2027, "month": 4, "label": "April 2027"},
    {"sequence": 6, "year": 2027, "month": 5, "label": "May 2027"},
    {"sequence": 7, "year": 2027, "month": 6, "label": "June 2027"},
    {"sequence": 8, "year": 2027, "month": 7, "label": "July 2027"},
    {"sequence": 9, "year": 2027, "month": 8, "label": "August 2027"},
    {"sequence": 10, "year": 2027, "month": 9, "label": "September 2027"},
    {"sequence": 11, "year": 2027, "month": 10, "label": "October 2027"},
    {"sequence": 12, "year": 2027, "month": 11, "label": "November 2027"},
    {"sequence": 13, "year": 2027, "month": 12, "label": "December 2027"},
]

# Month profiles: target brightness, warmth, drama for each slot
# brightness/warmth/drama each in [0, 1]
MONTH_PROFILES = [
    # seq, brightness, warmth, drama, earth_bonus, moon_bonus, crew_bonus, spacecraft_bonus
    (1, 0.3, 0.2, 0.9, 0.0, 0.0, 0.0, 0.3),  # Dec 2026 - launch, dramatic
    (2, 0.3, 0.2, 0.5, 0.0, 0.0, 0.0, 0.1),  # Jan - deep space
    (3, 0.3, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0),  # Feb - transit
    (4, 0.4, 0.4, 0.6, 0.0, 0.3, 0.0, 0.0),  # Mar - approaching Moon
    (5, 0.5, 0.4, 0.8, 0.2, 0.3, 0.1, 0.0),  # Apr - lunar orbit, drama
    (6, 0.5, 0.6, 0.5, 0.1, 0.1, 0.1, 0.2),  # May - return begins
    (7, 0.7, 0.8, 0.3, 0.2, 0.0, 0.1, 0.0),  # Jun - summer, bright
    (8, 0.7, 0.8, 0.3, 0.2, 0.0, 0.1, 0.0),  # Jul - summer
    (9, 0.6, 0.7, 0.4, 0.1, 0.0, 0.1, 0.0),  # Aug - late summer
    (10, 0.5, 0.5, 0.5, 0.1, 0.1, 0.0, 0.0),  # Sep - transition
    (11, 0.4, 0.3, 0.5, 0.0, 0.1, 0.0, 0.0),  # Oct - autumn
    (12, 0.3, 0.2, 0.6, 0.0, 0.0, 0.0, 0.0),  # Nov - pre-winter
    (13, 0.3, 0.2, 0.9, 0.0, 0.0, 0.1, 0.1),  # Dec 2027 - closing, dramatic
]


def _hue_to_warmth(hue: float, saturation: float) -> float:
    """Convert HSV hue (0-360) to warmth score (0-1).

    Low-saturation images (space scenes) get neutral warmth.
    """
    if saturation < 0.15:
        return 0.5

    # Warm hues: reds, oranges, yellows (0-60, 300-360)
    if hue <= 60 or hue >= 300:
        return 0.8 + 0.2 * (1 - min(hue, 360 - hue) / 60)
    # Cool hues: blues, cyans (180-260)
    elif 180 <= hue <= 260:
        return 0.2 * (1 - (hue - 180) / 80) if hue <= 220 else 0.2 * ((hue - 220) / 40)
    # Neutral (greens, purples)
    else:
        return 0.5


def _extract_dominant_hue_sat(dominant_color_json: str | None) -> tuple[float, float]:
    """Extract dominant color hue and saturation from JSON.

    Returns (hue in 0-360, saturation in 0-1).
    """
    if not dominant_color_json:
        return 0.0, 0.0

    try:
        colors = json.loads(dominant_color_json)
        if not colors:
            return 0.0, 0.0

        # Take the most dominant color (first entry, highest proportion)
        top = colors[0]
        r, g, b = top.get("r", 0), top.get("g", 0), top.get("b", 0)

        # Convert RGB (0-255) to HSV
        r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
        c_max = max(r_n, g_n, b_n)
        c_min = min(r_n, g_n, b_n)
        delta = c_max - c_min

        # Saturation
        sat = 0.0 if c_max == 0 else delta / c_max

        # Hue
        if delta == 0:
            hue = 0.0
        elif c_max == r_n:
            hue = 60 * (((g_n - b_n) / delta) % 6)
        elif c_max == g_n:
            hue = 60 * (((b_n - r_n) / delta) + 2)
        else:
            hue = 60 * (((r_n - g_n) / delta) + 4)

        return hue, sat
    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        return 0.0, 0.0


def compute_month_fit_scores(
    image_sks: list[int],
    brightness: dict[int, float],
    contrast: dict[int, float],
    saturation: dict[int, float],
    dominant_colors: dict[int, str | None],
    content_flags: dict[int, dict[str, bool]],
) -> dict[int, np.ndarray]:
    """Compute month-fit scores for each image across all 13 months.

    Returns dict mapping image_sk to a 13-element numpy array of fit scores in [0, 1].
    """
    result = {}

    for sk in image_sks:
        br = brightness.get(sk, 0.5)
        ct = contrast.get(sk, 0.5)
        sat = saturation.get(sk, 0.5)
        hue, hue_sat = _extract_dominant_hue_sat(dominant_colors.get(sk))
        warmth = _hue_to_warmth(hue, hue_sat)
        drama = min(1.0, ct * sat * 2)  # high contrast + high saturation = drama
        flags = content_flags.get(sk, {})

        scores = np.zeros(13, dtype=np.float64)

        for i, profile in enumerate(MONTH_PROFILES):
            _, tgt_br, tgt_warmth, tgt_drama, earth_b, moon_b, crew_b, spacecraft_b = profile

            # Distance-based fit (lower distance = better fit)
            br_dist = abs(br - tgt_br)
            warmth_dist = abs(warmth - tgt_warmth)
            drama_dist = abs(drama - tgt_drama)

            # Weighted distance
            fit = 1.0 - (0.30 * br_dist + 0.35 * warmth_dist + 0.35 * drama_dist)

            # Content flag bonuses
            if flags.get("earth") and earth_b > 0:
                fit += earth_b * 0.15
            if flags.get("moon") and moon_b > 0:
                fit += moon_b * 0.15
            if flags.get("crew") and crew_b > 0:
                fit += crew_b * 0.10
            if flags.get("spacecraft") and spacecraft_b > 0:
                fit += spacecraft_b * 0.10

            scores[i] = max(0.0, min(1.0, fit))

        result[sk] = scores

    logger.info(f"Computed month-fit scores for {len(result)} images")
    return result


def load_visual_data(
    conn,
) -> tuple[
    list[int],
    dict[int, float],
    dict[int, float],
    dict[int, float],
    dict[int, str | None],
    dict[int, dict[str, bool]],
]:
    """Load visual feature data needed for month-fit scoring.

    Returns (image_sks, brightness, contrast, saturation, dominant_colors, content_flags).
    """
    rows = conn.execute("""
        SELECT image_sk, brightness_score, contrast_score, saturation_score,
               dominant_color_json, has_earth_flag, has_moon_flag,
               has_crew_flag, has_spacecraft_flag
        FROM feature_image_visual
    """).fetchall()

    image_sks = []
    brightness = {}
    contrast = {}
    saturation = {}
    dominant_colors = {}
    content_flags = {}

    for r in rows:
        sk = int(r[0])
        image_sks.append(sk)
        brightness[sk] = float(r[1]) if r[1] is not None else 0.5
        contrast[sk] = float(r[2]) if r[2] is not None else 0.5
        saturation[sk] = float(r[3]) if r[3] is not None else 0.5
        dominant_colors[sk] = r[4]
        content_flags[sk] = {
            "earth": bool(r[5]),
            "moon": bool(r[6]),
            "crew": bool(r[7]),
            "spacecraft": bool(r[8]),
        }

    return image_sks, brightness, contrast, saturation, dominant_colors, content_flags
