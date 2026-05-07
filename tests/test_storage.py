"""Tests for the raw storage module."""

import pytest

from artemis_calendar.extract.storage import StorageConflictError, store_raw_artifact


def test_store_and_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr("artemis_calendar.extract.storage.RAW_ROOT", tmp_path)

    path = store_raw_artifact(b"content one", "test_source", "test.json", load_date="2026-01-01")
    assert path.exists()
    assert path.read_bytes() == b"content one"

    with pytest.raises(StorageConflictError):
        store_raw_artifact(b"content two", "test_source", "test.json", load_date="2026-01-01")


def test_store_different_dates(tmp_path, monkeypatch):
    monkeypatch.setattr("artemis_calendar.extract.storage.RAW_ROOT", tmp_path)

    p1 = store_raw_artifact(b"v1", "src", "data.json", load_date="2026-01-01")
    p2 = store_raw_artifact(b"v2", "src", "data.json", load_date="2026-01-02")
    assert p1 != p2
    assert p1.read_bytes() == b"v1"
    assert p2.read_bytes() == b"v2"
