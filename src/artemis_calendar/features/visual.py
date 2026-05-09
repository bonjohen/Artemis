"""Visual feature extraction from thumbnail images using Pillow."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import batched
from pathlib import Path

import duckdb
import numpy as np
from PIL import Image

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.features.visual")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"
FEATURE_WORKERS = 4
PROGRESS_EVERY = 1000


def _compute_orientation(width: int, height: int) -> str:
    ratio = width / height
    if ratio > 1.05:
        return "landscape"
    elif ratio < 0.95:
        return "portrait"
    return "square"


def _compute_brightness(img: Image.Image) -> float:
    """Mean L channel from LAB colorspace, normalized to [0, 1]."""
    lab = img.convert("LAB")
    l_channel = np.array(lab.split()[0], dtype=np.float64)
    return float(l_channel.mean() / 255.0)


def _compute_contrast(img: Image.Image) -> float:
    """Std of L channel from LAB colorspace, normalized to [0, 1]."""
    lab = img.convert("LAB")
    l_channel = np.array(lab.split()[0], dtype=np.float64)
    return float(l_channel.std() / 255.0)


def _compute_saturation(img: Image.Image) -> float:
    """Mean S channel from HSV, normalized to [0, 1]."""
    hsv = img.convert("HSV")
    s_channel = np.array(hsv.split()[1], dtype=np.float64)
    return float(s_channel.mean() / 255.0)


def _compute_dominant_colors(img: Image.Image, k: int = 5) -> list[dict]:
    """Pillow quantize for dominant colors — ~0.2ms vs 147ms for sklearn KMeans."""
    small = img.copy()
    small.thumbnail((100, 100))
    small_rgb = small.convert("RGB")
    q = small_rgb.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()
    hist = q.histogram()

    n_colors = max(idx for idx, v in enumerate(hist) if v > 0) + 1
    color_counts = [(hist[i], i) for i in range(n_colors) if hist[i] > 0]
    color_counts.sort(key=lambda x: -x[0])
    total = sum(c[0] for c in color_counts)

    colors = []
    for count, idx in color_counts[:k]:
        r, g, b = palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2]
        colors.append(
            {
                "r": r,
                "g": g,
                "b": b,
                "proportion": round(count / total, 4),
            }
        )
    return colors


def extract_visual_features_for_image(img: Image.Image) -> dict:
    """Extract all visual features from a PIL Image. Returns a flat dict."""
    width, height = img.size

    # Single LAB conversion for both brightness and contrast
    lab = img.convert("LAB")
    l_channel = np.array(lab.split()[0], dtype=np.float64)
    brightness = float(l_channel.mean() / 255.0)
    contrast = float(l_channel.std() / 255.0)

    # Saturation from HSV
    hsv = img.convert("HSV")
    s_channel = np.array(hsv.split()[1], dtype=np.float64)
    saturation = float(s_channel.mean() / 255.0)

    # Dark pixel ratio: fraction of pixels with luminance < 20
    gray = np.array(img.convert("L"))
    dark_pixel_ratio = float((gray < 20).mean())

    return {
        "orientation": _compute_orientation(width, height),
        "aspect_ratio": round(width / height, 4),
        "brightness_score": round(brightness, 4),
        "contrast_score": round(contrast, 4),
        "saturation_score": round(saturation, 4),
        "dominant_color_json": json.dumps(_compute_dominant_colors(img)),
        "dark_pixel_ratio": round(dark_pixel_ratio, 4),
    }


def _extract_one(image_sk: int, source_image_id: str, run_id: str, tdir: Path) -> tuple | None:
    """Extract features for one image. Returns INSERT tuple or None on failure."""
    thumb_path = tdir / f"{source_image_id}.jpg"
    if not thumb_path.exists():
        thumb_path = tdir / f"{source_image_id}.JPG"
    if not thumb_path.exists():
        return None

    try:
        img = Image.open(thumb_path)
        f = extract_visual_features_for_image(img)
        return (
            image_sk,
            run_id,
            f["orientation"],
            f["aspect_ratio"],
            f["brightness_score"],
            f["contrast_score"],
            f["saturation_score"],
            f["dominant_color_json"],
            f["dark_pixel_ratio"],
        )
    except Exception:
        logger.exception(f"Failed to extract features for {source_image_id}")
        return None


def extract_visual_features(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int | None = None,
    batch_size: int = 100,
    thumb_dir: Path | None = None,
) -> int:
    """Extract visual features for all images with downloaded thumbnails.

    Skips images that already have a row in feature_image_visual.
    Returns the number of images processed.
    """
    tdir = thumb_dir or THUMB_DIR
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="extract_visual",
        dataset_name="feature_image_visual",
        source_name="thumbnails",
    )

    query = """
        SELECT di.image_sk, di.source_image_id
        FROM dim_image di
        WHERE di.thumb_downloaded = true
          AND di.image_sk NOT IN (SELECT image_sk FROM feature_image_visual)
    """
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    logger.info(f"Found {len(rows)} images to extract visual features for")

    if not rows:
        update_run_status(conn, run_id, row_count_raw=0, row_count_loaded=0, load_status="complete")
        return 0

    # Extract features in parallel threads
    results: list[tuple] = []
    with ThreadPoolExecutor(max_workers=FEATURE_WORKERS) as executor:
        futures = {executor.submit(_extract_one, image_sk, sid, run_id, tdir): sid for image_sk, sid in rows}
        for done, future in enumerate(as_completed(futures), 1):
            row = future.result()
            if row is not None:
                results.append(row)
            if done % PROGRESS_EVERY == 0:
                logger.info(f"Extracted {done}/{len(rows)} images ({len(results)} ok)")

    # Batch insert all results
    for chunk in batched(results, 2000):
        chunk_list = list(chunk)
        conn.executemany(
            """
            INSERT INTO feature_image_visual (
                image_sk, feature_run_id, orientation, aspect_ratio,
                brightness_score, contrast_score, saturation_score,
                dominant_color_json, dark_pixel_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            chunk_list,
        )

    update_run_status(conn, run_id, row_count_raw=len(rows), row_count_loaded=len(results), load_status="complete")
    logger.info(f"Visual feature extraction complete: {len(results)}/{len(rows)} images")
    return len(results)
