"""Image downloader with resume, dedup, and rate limiting."""

import time

import duckdb

from artemis_calendar.config.settings import RATE_LIMIT_NASA, RATE_LIMIT_R2_CDN, RAW_ROOT
from artemis_calendar.extract.download import DownloadError, download_artifact
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.images")

R2_BASE = "https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev"
NASA_BASE = "https://eol.jsc.nasa.gov/DatabaseImages/ESC/large/ART002"

THUMB_DIR = RAW_ROOT / "images" / "thumbs"
LARGE_DIR = RAW_ROOT / "images" / "large"


def _get_pending_images(
    conn: duckdb.DuckDBPyConnection,
    thumbs: bool = True,
    full: bool = False,
    limit: int | None = None,
) -> list[str]:
    """Get GUIDs of images that need downloading."""
    conditions = []
    if thumbs:
        conditions.append("thumb_downloaded = false")
    if full:
        conditions.append("full_downloaded = false")
    if not conditions:
        return []

    where = " OR ".join(conditions)
    query = f"SELECT source_image_id FROM dim_image WHERE vote_pool_flag = true AND ({where})"
    if limit:
        query += f" LIMIT {limit}"
    return [row[0] for row in conn.execute(query).fetchall()]


def download_thumbnails(
    conn: duckdb.DuckDBPyConnection,
    limit: int | None = None,
    rate_limit: float = RATE_LIMIT_R2_CDN,
) -> int:
    """Download thumbnail images from R2 CDN. Returns count of newly downloaded."""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    guids = _get_pending_images(conn, thumbs=True, full=False, limit=limit)
    logger.info(f"Thumbnails to download: {len(guids)}")

    downloaded = 0
    for guid in guids:
        dest = THUMB_DIR / f"{guid}.jpg"
        if dest.exists():
            # Already on disk — just update the flag
            conn.execute(
                "UPDATE dim_image SET thumb_downloaded = true, updated_at = now() WHERE source_image_id = ?",
                [guid],
            )
            continue

        url = f"{R2_BASE}/thumbs/{guid}.jpg"
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="collect-images",
            dataset_name="thumbnail",
            source_name=guid,
            source_url=url,
        )

        try:
            result = download_artifact(url, timeout=30.0)
            dest.write_bytes(result.content)
            conn.execute(
                "UPDATE dim_image SET thumb_downloaded = true, updated_at = now() WHERE source_image_id = ?",
                [guid],
            )
            update_run_status(
                conn,
                run_id,
                row_count_raw=len(result.content),
                load_status="success",
            )
            conn.execute(
                "UPDATE run_manifest SET raw_checksum = ?, raw_file_path = ? WHERE run_id = ?",
                [result.checksum, str(dest), run_id],
            )
            downloaded += 1
            if (downloaded % 50) == 0:
                logger.info(f"Downloaded {downloaded}/{len(guids)} thumbnails")
        except DownloadError as e:
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))
            logger.debug(f"Failed thumbnail {guid}: {e}")

        if rate_limit > 0:
            time.sleep(rate_limit)

    logger.info(f"Thumbnail download complete: {downloaded} new")
    return downloaded


def download_full_images(
    conn: duckdb.DuckDBPyConnection,
    limit: int | None = None,
    rate_limit: float = RATE_LIMIT_NASA,
) -> int:
    """Download full-resolution images from NASA JSC. Returns count of newly downloaded."""
    LARGE_DIR.mkdir(parents=True, exist_ok=True)
    guids = _get_pending_images(conn, thumbs=False, full=True, limit=limit)
    logger.info(f"Full images to download: {len(guids)}")

    downloaded = 0
    for guid in guids:
        dest = LARGE_DIR / f"{guid}.JPG"
        if dest.exists():
            conn.execute(
                "UPDATE dim_image SET full_downloaded = true, updated_at = now() WHERE source_image_id = ?",
                [guid],
            )
            continue

        url = f"{NASA_BASE}/{guid}.JPG"
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="collect-images",
            dataset_name="full_image",
            source_name=guid,
            source_url=url,
        )

        try:
            result = download_artifact(url, timeout=60.0)
            dest.write_bytes(result.content)
            conn.execute(
                "UPDATE dim_image SET full_downloaded = true, updated_at = now() WHERE source_image_id = ?",
                [guid],
            )
            update_run_status(
                conn,
                run_id,
                row_count_raw=len(result.content),
                load_status="success",
            )
            conn.execute(
                "UPDATE run_manifest SET raw_checksum = ?, raw_file_path = ? WHERE run_id = ?",
                [result.checksum, str(dest), run_id],
            )
            downloaded += 1
            if (downloaded % 10) == 0:
                logger.info(f"Downloaded {downloaded}/{len(guids)} full images")
        except DownloadError as e:
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))
            logger.debug(f"Failed full image {guid}: {e}")

        if rate_limit > 0:
            time.sleep(rate_limit)

    logger.info(f"Full image download complete: {downloaded} new")
    return downloaded
