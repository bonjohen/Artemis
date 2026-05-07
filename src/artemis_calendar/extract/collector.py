"""Metadata collection orchestrator — download, dedup, archive, and log all sources."""

from datetime import UTC, datetime

import duckdb

from artemis_calendar.config.settings import MANIFEST_PATH, TIMESTAMP_FORMAT
from artemis_calendar.extract.download import DownloadError, download_artifact
from artemis_calendar.extract.manifest import ManifestEntry, load_manifest
from artemis_calendar.extract.storage import StorageConflictError, store_raw_artifact
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.collect")

# Map source names to their canonical archive filenames
_ARCHIVE_FILENAMES = {
    "timeline_photos_js": "photos.js",
    "vote_manifest": "manifest.json",
    "category_index": "index.json",
    "leaderboard_batch": "top.json",
    "leaderboard_elo": "elo-top.json",
    "vote_counts": "count.json",
}


def _check_already_collected(conn: duckdb.DuckDBPyConnection, source_name: str, checksum: str) -> bool:
    """Return True if this source was already collected with the same checksum."""
    row = conn.execute("SELECT last_checksum FROM source_manifest WHERE source_name = ?", [source_name]).fetchone()
    return row is not None and row[0] == checksum


def _upsert_source_manifest(
    conn: duckdb.DuckDBPyConnection, entry: ManifestEntry, checksum: str, changed: bool
) -> None:
    """Update source_manifest with latest check results."""
    now = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
    existing = conn.execute("SELECT 1 FROM source_manifest WHERE source_name = ?", [entry.source_name]).fetchone()

    if existing:
        if changed:
            conn.execute(
                """UPDATE source_manifest
                   SET last_checked_at = ?, last_checksum = ?, last_changed_at = ?
                   WHERE source_name = ?""",
                [now, checksum, now, entry.source_name],
            )
        else:
            conn.execute(
                "UPDATE source_manifest SET last_checked_at = ? WHERE source_name = ?",
                [now, entry.source_name],
            )
    else:
        conn.execute(
            """INSERT INTO source_manifest
               (source_name, source_type, source_url, expected_format, refresh_frequency, active_flag,
                last_checked_at, last_checksum, last_changed_at, notes)
               VALUES (?, ?, ?, ?, ?, true, ?, ?, ?, ?)""",
            [
                entry.source_name,
                entry.source_type,
                entry.source_url,
                entry.expected_format,
                entry.refresh_frequency,
                now,
                checksum,
                now,
                entry.notes,
            ],
        )


def collect_source(conn: duckdb.DuckDBPyConnection, entry: ManifestEntry) -> str:
    """Collect a single source: download, dedup, archive, log. Returns run_id."""
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="collect-metadata",
        dataset_name=entry.source_name,
        source_name=entry.source_name,
        source_url=entry.source_url,
    )

    try:
        logger.info(
            f"Downloading {entry.source_name} from {entry.source_url}",
            extra={"run_id": run_id, "source_name": entry.source_name},
        )
        result = download_artifact(entry.source_url)

        if _check_already_collected(conn, entry.source_name, result.checksum):
            logger.info(
                f"Skipping {entry.source_name}: checksum unchanged ({result.checksum[:12]}...)",
                extra={"run_id": run_id, "source_name": entry.source_name},
            )
            update_run_status(
                conn,
                run_id,
                load_status="skipped",
                skip_reason="already_collected",
                row_count_raw=len(result.content),
            )
            _upsert_source_manifest(conn, entry, result.checksum, changed=False)
            return run_id

        filename = _ARCHIVE_FILENAMES.get(entry.source_name, f"{entry.source_name}.dat")
        try:
            raw_path = store_raw_artifact(result.content, entry.source_name, filename)
        except StorageConflictError:
            # Same date partition already has a file — still log as success
            raw_path = None

        logger.info(
            f"Archived {entry.source_name}: {len(result.content):,} bytes, checksum={result.checksum[:12]}...",
            extra={"run_id": run_id, "source_name": entry.source_name},
        )

        update_run_status(
            conn,
            run_id,
            load_status="success",
            row_count_raw=len(result.content),
        )
        # Update raw_checksum and raw_file_path on the run record
        conn.execute(
            "UPDATE run_manifest SET raw_checksum = ?, raw_file_path = ? WHERE run_id = ?",
            [result.checksum, str(raw_path) if raw_path else None, run_id],
        )
        _upsert_source_manifest(conn, entry, result.checksum, changed=True)

    except DownloadError as e:
        logger.error(
            f"Failed to download {entry.source_name}: {e}",
            extra={"run_id": run_id, "source_name": entry.source_name},
        )
        update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    except Exception as e:
        logger.error(
            f"Unexpected error collecting {entry.source_name}: {e}",
            extra={"run_id": run_id, "source_name": entry.source_name},
        )
        update_run_status(conn, run_id, load_status="failed", failure_message=str(e))

    return run_id


def collect_all_metadata(conn: duckdb.DuckDBPyConnection, manifest_path: str | None = None) -> list[str]:
    """Collect all sources defined in the manifest. Returns list of run_ids."""
    path = manifest_path or str(MANIFEST_PATH)
    entries = load_manifest(path)
    run_ids = []
    for entry in entries:
        run_id = collect_source(conn, entry)
        run_ids.append(run_id)
    return run_ids
