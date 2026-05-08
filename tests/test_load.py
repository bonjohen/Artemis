"""Tests for load/loader.py metadata loading functions."""

import duckdb
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """In-memory DuckDB with migrations applied."""
    c = duckdb.connect(":memory:")
    apply_migrations(c, migrations_dir=MIGRATIONS_DIR)
    yield c
    c.close()


class TestLoadTimelinePhotos:
    def test_loads_photos_into_staging(self, conn):
        from artemis_calendar.load.staging import load_timeline_photos

        photos = [
            {
                "file": "NHQ202501010001",
                "title": "Test Photo",
                "flickr_desc": "A description",
                "photographer": "Tester",
                "location": "KSC",
                "camera": "Nikon",
                "settings": "f/2.8",
                "time": "2025-01-01T00:00:00Z",
                "spacecraft": True,
                "batch": 1,
                "enabled": True,
                "camera_id": "cam1",
            },
            {
                "file": "NHQ202501010002",
                "title": "Second Photo",
                "flickr_desc": None,
                "photographer": None,
                "location": None,
                "camera": None,
                "settings": None,
                "time": None,
                "spacecraft": False,
                "batch": None,
                "enabled": True,
                "camera_id": None,
            },
        ]
        count = load_timeline_photos(conn, "test-run-001", photos)
        assert count == 2
        rows = conn.execute("SELECT COUNT(*) FROM stg_timeline_photo WHERE load_run_id = 'test-run-001'").fetchone()[0]
        assert rows == 2


class TestLoadVoteManifest:
    def test_loads_manifest_items(self, conn):
        from artemis_calendar.load.staging import load_vote_manifest_images

        items = [
            {"guid": "ART002-E-10001", "link": "https://example.com/1"},
            {"guid": "ART002-E-10002", "link": "https://example.com/2"},
            {"guid": "ART002-E-10003", "link": None},
        ]
        count = load_vote_manifest_images(conn, "test-run-vm", items)
        assert count == 3
        rows = conn.execute(
            "SELECT COUNT(*) FROM stg_vote_manifest_image WHERE load_run_id = 'test-run-vm'"
        ).fetchone()[0]
        assert rows == 3

    def test_loads_empty_manifest(self, conn):
        from artemis_calendar.load.staging import load_vote_manifest_images

        count = load_vote_manifest_images(conn, "test-run-empty", [])
        assert count == 0


class TestLoadCategories:
    def test_loads_categories(self, conn):
        from artemis_calendar.load.staging import load_categories

        categories = [
            {"key": "earth", "slug": "earth", "label": "Earth Views", "count": 100, "showcase": "ART002-E-10001"},
            {"key": "crew", "slug": "crew", "label": "Crew", "count": 50, "showcase": "ART002-E-10002"},
        ]
        count = load_categories(conn, "test-run-cat", categories)
        assert count == 2
        rows = conn.execute("SELECT COUNT(*) FROM stg_category WHERE load_run_id = 'test-run-cat'").fetchone()[0]
        assert rows == 2
