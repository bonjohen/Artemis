"""Run manifest operations — create, update, and query pipeline run records."""

import uuid
from datetime import UTC, datetime

import duckdb

from artemis_calendar.config.settings import TIMESTAMP_FORMAT


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return str(uuid.uuid4())


def create_run_record(
    conn: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    pipeline_name: str,
    dataset_name: str,
    source_name: str,
    source_url: str | None = None,
    raw_checksum: str | None = None,
    raw_file_path: str | None = None,
) -> str:
    """Insert a new run manifest record. Returns the run_id."""
    conn.execute(
        """
        INSERT INTO run_manifest (
            run_id, pipeline_name, dataset_name, source_name,
            source_url, raw_checksum, raw_file_path,
            downloaded_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            pipeline_name,
            dataset_name,
            source_name,
            source_url,
            raw_checksum,
            raw_file_path,
            datetime.now(UTC).strftime(TIMESTAMP_FORMAT),
            datetime.now(UTC).strftime(TIMESTAMP_FORMAT),
        ],
    )
    return run_id


def update_run_status(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    *,
    row_count_raw: int | None = None,
    row_count_loaded: int | None = None,
    load_status: str | None = None,
    skip_reason: str | None = None,
    failure_message: str | None = None,
) -> None:
    """Update run manifest with counts and completion status."""
    conn.execute(
        """
        UPDATE run_manifest SET
            row_count_raw = COALESCE(?, row_count_raw),
            row_count_loaded = COALESCE(?, row_count_loaded),
            load_status = COALESCE(?, load_status),
            skip_reason = COALESCE(?, skip_reason),
            failure_message = COALESCE(?, failure_message),
            completed_at = ?
        WHERE run_id = ?
        """,
        [
            row_count_raw,
            row_count_loaded,
            load_status,
            skip_reason,
            failure_message,
            datetime.now(UTC).strftime(TIMESTAMP_FORMAT),
            run_id,
        ],
    )


def get_run(conn: duckdb.DuckDBPyConnection, run_id: str) -> dict | None:
    """Fetch a single run manifest record as a dict."""
    result = conn.execute("SELECT * FROM run_manifest WHERE run_id = ?", [run_id]).fetchone()
    if not result:
        return None
    columns = [desc[0] for desc in conn.description]
    return dict(zip(columns, result, strict=False))
