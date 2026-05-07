"""Load staging data into warehouse dimension tables."""

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.warehouse")


def load_dim_image_from_timeline(conn: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """Merge stg_timeline_photo into dim_image.

    Timeline photos use file_name as the source_image_id (they don't have GUIDs).
    Sets timeline_flag = true.
    """
    result = conn.execute(
        """
        INSERT INTO dim_image (source_image_id, source_file_name, title, description,
                               photographer, location, camera, settings, taken_at_str,
                               spacecraft_flag, enabled_flag, timeline_flag)
        SELECT file_name, file_name, title, description,
               photographer, location, camera, settings, time_str,
               spacecraft, enabled, true
        FROM stg_timeline_photo
        WHERE load_run_id = ?
          AND file_name NOT IN (SELECT source_image_id FROM dim_image)
        """,
        [run_id],
    )
    count = result.fetchone()[0] if result.description else 0
    # DuckDB INSERT doesn't return count directly; count the new rows
    count = conn.execute("SELECT count(*) FROM dim_image WHERE timeline_flag = true").fetchone()[0]
    logger.info(f"dim_image timeline photos: {count}")
    return count


def load_dim_image_from_vote_manifest(conn: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """Merge stg_vote_manifest_image into dim_image.

    Vote manifest images use guid as source_image_id.
    Sets vote_pool_flag = true.
    """
    # Insert new GUIDs not yet in dim_image
    conn.execute(
        """
        INSERT INTO dim_image (source_image_id, vote_pool_flag)
        SELECT guid, true
        FROM stg_vote_manifest_image
        WHERE load_run_id = ?
          AND guid NOT IN (SELECT source_image_id FROM dim_image)
        """,
        [run_id],
    )
    # Update existing rows to set vote_pool_flag
    conn.execute(
        """
        UPDATE dim_image SET vote_pool_flag = true, updated_at = now()
        WHERE source_image_id IN (
            SELECT guid FROM stg_vote_manifest_image WHERE load_run_id = ?
        )
        """,
        [run_id],
    )
    count = conn.execute("SELECT count(*) FROM dim_image WHERE vote_pool_flag = true").fetchone()[0]
    logger.info(f"dim_image vote pool images: {count}")
    return count


def load_dim_category(conn: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """Merge stg_category into dim_category."""
    conn.execute(
        """
        INSERT INTO dim_category (category_key, category_slug, category_label, image_count)
        SELECT category_key, category_slug, category_label, image_count
        FROM stg_category
        WHERE load_run_id = ?
          AND category_key NOT IN (SELECT category_key FROM dim_category)
        """,
        [run_id],
    )
    # Update existing
    conn.execute(
        """
        UPDATE dim_category SET
            category_label = s.category_label,
            image_count = s.image_count
        FROM stg_category s
        WHERE dim_category.category_key = s.category_key
          AND s.load_run_id = ?
        """,
        [run_id],
    )
    count = conn.execute("SELECT count(*) FROM dim_category").fetchone()[0]
    logger.info(f"dim_category: {count} categories")
    return count
