"""Visual feature extraction from thumbnail images using Pillow."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
from PIL import Image

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.features.visual")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"


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
    """K-means clustering on downsampled pixel colors. Returns k dominant colors."""
    from sklearn.cluster import KMeans

    # Downsample for speed
    small = img.copy()
    small.thumbnail((100, 100))
    pixels = np.array(small.convert("RGB")).reshape(-1, 3).astype(np.float64)

    kmeans = KMeans(n_clusters=min(k, len(pixels)), random_state=42, n_init=3)
    kmeans.fit(pixels)

    # Sort by cluster size descending
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    order = np.argsort(-counts)

    colors = []
    total = len(pixels)
    for idx in order:
        center = kmeans.cluster_centers_[labels[idx]]
        colors.append({
            "r": int(round(center[0])),
            "g": int(round(center[1])),
            "b": int(round(center[2])),
            "proportion": round(float(counts[idx]) / total, 4),
        })
    return colors


def extract_visual_features_for_image(img: Image.Image) -> dict:
    """Extract all visual features from a PIL Image. Returns a flat dict."""
    width, height = img.size
    return {
        "orientation": _compute_orientation(width, height),
        "aspect_ratio": round(width / height, 4),
        "brightness_score": round(_compute_brightness(img), 4),
        "contrast_score": round(_compute_contrast(img), 4),
        "saturation_score": round(_compute_saturation(img), 4),
        "dominant_color_json": json.dumps(_compute_dominant_colors(img)),
    }


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

    # Get images with thumbs that haven't been feature-extracted yet
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

    processed = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        for image_sk, source_image_id in batch:
            # Try both .jpg and .JPG extensions
            thumb_path = tdir / f"{source_image_id}.jpg"
            if not thumb_path.exists():
                thumb_path = tdir / f"{source_image_id}.JPG"
            if not thumb_path.exists():
                logger.debug(f"No thumbnail for {source_image_id}, skipping")
                continue

            try:
                img = Image.open(thumb_path)
                features = extract_visual_features_for_image(img)
                conn.execute(
                    """
                    INSERT INTO feature_image_visual (
                        image_sk, feature_run_id, orientation, aspect_ratio,
                        brightness_score, contrast_score, saturation_score,
                        dominant_color_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        image_sk,
                        run_id,
                        features["orientation"],
                        features["aspect_ratio"],
                        features["brightness_score"],
                        features["contrast_score"],
                        features["saturation_score"],
                        features["dominant_color_json"],
                    ],
                )
                processed += 1
            except Exception:
                logger.exception(f"Failed to extract features for {source_image_id}")

        logger.info(f"Processed {min(i + batch_size, len(rows))}/{len(rows)} images")

    update_run_status(conn, run_id, row_count_raw=len(rows), row_count_loaded=processed, load_status="complete")
    logger.info(f"Visual feature extraction complete: {processed}/{len(rows)} images")
    return processed
