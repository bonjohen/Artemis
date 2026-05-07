"""Image downloader with resume, dedup, and concurrent downloads."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import batched
from pathlib import Path

import duckdb
import httpx

from artemis_calendar.config.settings import RATE_LIMIT_NASA, RAW_ROOT, THUMB_DOWNLOAD_WORKERS
from artemis_calendar.extract.download import DownloadError, download_artifact
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.images")

R2_BASE = "https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev"
NASA_BASE = "https://eol.jsc.nasa.gov/DatabaseImages/ESC/large/ART002"

THUMB_DIR = RAW_ROOT / "images" / "thumbs"
LARGE_DIR = RAW_ROOT / "images" / "large"

PROGRESS_EVERY = 500
DB_BATCH_SIZE = 2000


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


def _download_one_thumb(client: httpx.Client, guid: str, dest_dir: Path) -> tuple[str, bool, str | None]:
    """Download a single thumbnail. Returns (guid, success, error_message)."""
    dest = dest_dir / f"{guid}.jpg"
    if dest.exists():
        return (guid, True, None)

    url = f"{R2_BASE}/thumbs/{guid}.jpg"
    try:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return (guid, True, None)
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError, OSError) as e:
        return (guid, False, str(e))


def _flush_succeeded(conn: duckdb.DuckDBPyConnection, guids: list[str]) -> None:
    """Batch-update dim_image for successfully downloaded thumbnails."""
    for chunk in batched(guids, DB_BATCH_SIZE):
        chunk_list = list(chunk)
        conn.execute(
            "UPDATE dim_image SET thumb_downloaded = true, updated_at = now() "
            "WHERE source_image_id IN (SELECT unnest($1::VARCHAR[]))",
            [chunk_list],
        )


def download_thumbnails(
    conn: duckdb.DuckDBPyConnection,
    limit: int | None = None,
    rate_limit: float = 0.0,  # kept for CLI compat, unused in concurrent mode
    workers: int = THUMB_DOWNLOAD_WORKERS,
) -> int:
    """Download thumbnail images from R2 CDN concurrently. Returns count of newly downloaded."""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    guids = _get_pending_images(conn, thumbs=True, full=False, limit=limit)
    if not guids:
        logger.info("No thumbnails to download.")
        return 0

    logger.info(f"Thumbnails to download: {len(guids)} (workers={workers})")

    # Single run manifest record for the batch
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="collect-images",
        dataset_name="thumbnail_batch",
        source_name=f"batch-{len(guids)}",
        source_url=f"{R2_BASE}/thumbs/",
    )

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []

    try:
        with (
            httpx.Client(
                timeout=20.0,
                follow_redirects=True,
                http2=True,
                limits=httpx.Limits(
                    max_connections=workers,
                    max_keepalive_connections=workers,
                ),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
            ) as client,
            ThreadPoolExecutor(max_workers=workers) as executor,
        ):
            futures = {executor.submit(_download_one_thumb, client, guid, THUMB_DIR): guid for guid in guids}

            for i, future in enumerate(as_completed(futures), 1):
                guid, ok, err = future.result()
                if ok:
                    succeeded.append(guid)
                else:
                    failed.append((guid, err or "unknown"))

                if i % PROGRESS_EVERY == 0:
                    logger.info(f"Progress: {i}/{len(guids)} processed, {len(succeeded)} ok, {len(failed)} failed")
    finally:
        # Flush whatever succeeded to DB even on interrupt
        if succeeded:
            _flush_succeeded(conn, succeeded)
            logger.info(f"Flushed {len(succeeded)} successful downloads to DB")

        status = "success" if not failed else "partial"
        failure_msg = f"{len(failed)} failures" if failed else None
        update_run_status(
            conn,
            run_id,
            row_count_raw=len(succeeded),
            load_status=status,
            failure_message=failure_msg,
        )

    if failed:
        logger.warning(f"Failed thumbnails: {len(failed)}")
        for guid, err in failed[:10]:
            logger.debug(f"  {guid}: {err}")
        if len(failed) > 10:
            logger.debug(f"  ... and {len(failed) - 10} more")

    logger.info(f"Thumbnail download complete: {len(succeeded)} new, {len(failed)} failed")
    return len(succeeded)


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


def download_candidate_images(
    conn: duckdb.DuckDBPyConnection,
    candidate_name: str,
    run_id: str | None = None,
) -> int:
    """Download full-resolution images for a specific calendar candidate.

    Only downloads the 13 images assigned to the candidate, not all 12,217.
    Returns count of newly downloaded images.
    """
    LARGE_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve run_id if not provided
    if run_id is None:
        row = conn.execute(
            "SELECT candidate_run_id FROM mart_calendar_candidate ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            logger.warning("No calendar candidates found in warehouse")
            return 0
        run_id = row[0]

    # Get the 13 GUIDs for this candidate
    rows = conn.execute(
        """
        SELECT DISTINCT d.source_image_id
        FROM mart_calendar_candidate_month_image m
        JOIN dim_image d ON d.image_sk = m.image_sk
        WHERE m.candidate_name = ? AND m.candidate_run_id = ?
        """,
        [candidate_name, run_id],
    ).fetchall()

    guids = [r[0] for r in rows]
    if not guids:
        logger.warning(f"No images found for candidate {candidate_name} (run {run_id})")
        return 0

    logger.info(f"Downloading {len(guids)} full-resolution images for candidate {candidate_name}")

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
        try:
            result = download_artifact(url, timeout=60.0)
            dest.write_bytes(result.content)
            conn.execute(
                "UPDATE dim_image SET full_downloaded = true, updated_at = now() WHERE source_image_id = ?",
                [guid],
            )
            downloaded += 1
            logger.info(f"Downloaded {guid} ({downloaded}/{len(guids)})")
        except DownloadError as e:
            logger.warning(f"Failed to download {guid}: {e}")

        if RATE_LIMIT_NASA > 0:
            time.sleep(RATE_LIMIT_NASA)

    logger.info(f"Candidate image download complete: {downloaded} new, {len(guids) - downloaded} already on disk")
    return downloaded
