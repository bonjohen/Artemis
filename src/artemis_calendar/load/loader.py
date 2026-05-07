"""Metadata load orchestrator — parse raw files and load into staging + warehouse."""

from pathlib import Path

import duckdb

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.load.staging import (
    load_batch_leaderboard,
    load_categories,
    load_elo_leaderboard,
    load_timeline_photos,
    load_vote_counts,
    load_vote_manifest_images,
)
from artemis_calendar.load.warehouse import (
    load_dim_category,
    load_dim_image_from_timeline,
    load_dim_image_from_vote_manifest,
)
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status
from artemis_calendar.parse.category_parser import parse_category_index
from artemis_calendar.parse.leaderboard_parser import parse_batch_leaderboard, parse_elo_leaderboard, parse_vote_counts
from artemis_calendar.parse.timeline_parser import parse_photos_js
from artemis_calendar.parse.vote_manifest_parser import parse_vote_manifest

logger = get_logger("artemis.loader")


def _find_latest_raw(source_name: str, filename: str) -> Path | None:
    """Find the most recent raw file for a source by date partition."""
    source_dir = RAW_ROOT / "artemistimeline" / source_name
    if not source_dir.exists():
        return None
    partitions = sorted(source_dir.glob("load_date=*"), reverse=True)
    for p in partitions:
        candidate = p / filename
        if candidate.exists():
            return candidate
    return None


def load_all_metadata(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Parse all latest raw files and load into staging + warehouse. Returns row counts."""
    counts = {}

    # Timeline photos
    raw_file = _find_latest_raw("timeline_photos_js", "photos.js")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="load-metadata",
            dataset_name="timeline_photos",
            source_name="timeline_photos_js",
        )
        try:
            photos = parse_photos_js(raw_file.read_bytes())
            stg_count = load_timeline_photos(conn, run_id, photos)
            wh_count = load_dim_image_from_timeline(conn, run_id)
            update_run_status(conn, run_id, row_count_raw=stg_count, row_count_loaded=wh_count, load_status="success")
            counts["stg_timeline_photo"] = stg_count
            logger.info(f"Loaded {stg_count} timeline photos, {wh_count} in dim_image")
        except Exception as e:
            logger.error(f"Failed to load timeline photos: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))
    else:
        logger.warning("No raw photos.js found — run collect-metadata first")

    # Vote manifest
    raw_file = _find_latest_raw("vote_manifest", "manifest.json")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="load-metadata",
            dataset_name="vote_manifest",
            source_name="vote_manifest",
        )
        try:
            _meta, items = parse_vote_manifest(raw_file.read_bytes())
            stg_count = load_vote_manifest_images(conn, run_id, items)
            wh_count = load_dim_image_from_vote_manifest(conn, run_id)
            update_run_status(conn, run_id, row_count_raw=stg_count, row_count_loaded=wh_count, load_status="success")
            counts["stg_vote_manifest_image"] = stg_count
            logger.info(f"Loaded {stg_count} vote manifest images, {wh_count} in dim_image vote pool")
        except Exception as e:
            logger.error(f"Failed to load vote manifest: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    # Categories
    raw_file = _find_latest_raw("category_index", "index.json")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn, run_id=run_id, pipeline_name="load-metadata", dataset_name="categories", source_name="category_index"
        )
        try:
            categories = parse_category_index(raw_file.read_bytes())
            stg_count = load_categories(conn, run_id, categories)
            wh_count = load_dim_category(conn, run_id)
            update_run_status(conn, run_id, row_count_raw=stg_count, row_count_loaded=wh_count, load_status="success")
            counts["stg_category"] = stg_count
            logger.info(f"Loaded {stg_count} categories, {wh_count} in dim_category")
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    # Batch leaderboard
    raw_file = _find_latest_raw("leaderboard_batch", "top.json")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="load-metadata",
            dataset_name="leaderboard_batch",
            source_name="leaderboard_batch",
        )
        try:
            entries = parse_batch_leaderboard(raw_file.read_bytes())
            stg_count = load_batch_leaderboard(conn, run_id, entries)
            update_run_status(conn, run_id, row_count_raw=stg_count, load_status="success")
            counts["stg_leaderboard_batch"] = stg_count
            logger.info(f"Loaded {stg_count} batch leaderboard entries")
        except Exception as e:
            logger.error(f"Failed to load batch leaderboard: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    # Elo leaderboard
    raw_file = _find_latest_raw("leaderboard_elo", "elo-top.json")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn,
            run_id=run_id,
            pipeline_name="load-metadata",
            dataset_name="leaderboard_elo",
            source_name="leaderboard_elo",
        )
        try:
            entries = parse_elo_leaderboard(raw_file.read_bytes())
            stg_count = load_elo_leaderboard(conn, run_id, entries)
            update_run_status(conn, run_id, row_count_raw=stg_count, load_status="success")
            counts["stg_leaderboard_elo"] = stg_count
            logger.info(f"Loaded {stg_count} Elo leaderboard entries")
        except Exception as e:
            logger.error(f"Failed to load Elo leaderboard: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    # Vote counts
    raw_file = _find_latest_raw("vote_counts", "count.json")
    if raw_file:
        run_id = generate_run_id()
        create_run_record(
            conn, run_id=run_id, pipeline_name="load-metadata", dataset_name="vote_counts", source_name="vote_counts"
        )
        try:
            data = parse_vote_counts(raw_file.read_bytes())
            stg_count = load_vote_counts(conn, run_id, data)
            update_run_status(conn, run_id, row_count_raw=stg_count, load_status="success")
            counts["stg_vote_counts"] = stg_count
            logger.info(f"Loaded vote counts: {data}")
        except Exception as e:
            logger.error(f"Failed to load vote counts: {e}")
            update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    return counts
