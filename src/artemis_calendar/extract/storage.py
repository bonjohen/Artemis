"""Raw storage writer — immutable artifact storage with date-partitioned paths."""

from datetime import UTC, datetime
from pathlib import Path

from artemis_calendar.config.settings import RAW_ROOT


class StorageConflictError(Exception):
    """Raised when attempting to overwrite an existing raw artifact."""


def build_raw_path(source_name: str, filename: str, load_date: str | None = None) -> Path:
    """Build the canonical raw archive path for a source artifact."""
    if load_date is None:
        load_date = datetime.now(UTC).strftime("%Y-%m-%d")
    return RAW_ROOT / "artemistimeline" / source_name / f"load_date={load_date}" / filename


def store_raw_artifact(content: bytes, source_name: str, filename: str, load_date: str | None = None) -> Path:
    """Store a raw artifact immutably at the canonical path.

    Raises StorageConflictError if the file already exists.
    Returns the path where the file was written.
    """
    path = build_raw_path(source_name, filename, load_date)

    if path.exists():
        raise StorageConflictError(f"Raw artifact already exists at {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
