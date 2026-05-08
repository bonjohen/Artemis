"""Tests for the web API endpoints."""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from artemis_calendar.web.app import create_app


@pytest.fixture()
def db():
    """Create an in-memory DuckDB with the tables needed for web API."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE dim_image (
            image_sk INTEGER PRIMARY KEY,
            source_image_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            vote_pool BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE mart_image_preference_score (
            image_sk INTEGER,
            score_run_id TEXT,
            posterior_mean DOUBLE,
            elo_score DOUBLE,
            borda_score DOUBLE,
            broad_appeal_score DOUBLE,
            uncertainty_score DOUBLE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE feature_image_visual (
            image_sk INTEGER,
            brightness_score DOUBLE,
            contrast_score DOUBLE,
            saturation_score DOUBLE,
            dominant_color_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE feature_image_cluster (
            image_sk INTEGER,
            cluster_type TEXT,
            cluster_id INTEGER,
            cluster_run_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE mart_calendar_candidate (
            candidate_name TEXT,
            candidate_run_id TEXT,
            cover_image_sk INTEGER,
            objective_score DOUBLE,
            popularity_score DOUBLE,
            diversity_score DOUBLE,
            month_fit_score DOUBLE,
            cover_fit_score DOUBLE,
            redundancy_penalty DOUBLE,
            uncertainty_penalty DOUBLE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE mart_calendar_candidate_month_image (
            candidate_run_id TEXT,
            candidate_name TEXT,
            sequence_number INTEGER,
            month_label TEXT,
            image_sk INTEGER,
            month_fit_score DOUBLE,
            preference_score DOUBLE
        )
    """)

    # Seed data
    for i in range(5):
        conn.execute(
            "INSERT INTO dim_image (image_sk, source_image_id, title, vote_pool) VALUES (?, ?, ?, true)",
            [13775 + i, f"GUID{i:04d}", f"Image {i}"],
        )
        conn.execute(
            "INSERT INTO mart_image_preference_score VALUES (?, 'run1', ?, ?, ?, ?, ?, now())",
            [13775 + i, 0.5 + i * 0.1, 1500 + i * 10, 3.0 + i * 0.5, 0.6 + i * 0.05, 0.1 + i * 0.02],
        )
        conn.execute(
            "INSERT INTO feature_image_visual VALUES (?, ?, ?, ?, ?)",
            [13775 + i, 0.5 + i * 0.05, 0.4 + i * 0.03, 0.6 + i * 0.02, '{"r":100,"g":150,"b":200}'],
        )
        conn.execute(
            "INSERT INTO feature_image_cluster VALUES (?, 'visual', ?, 'crun1', now())",
            [13775 + i, i % 3],
        )

    # Seed candidate
    conn.execute(
        "INSERT INTO mart_calendar_candidate VALUES "
        "('method_a', 'run1', 13775, 5.0, 8.0, 0.7, 5.5, 0.65, 0.25, 0.8, now())"
    )
    conn.execute(
        "INSERT INTO mart_calendar_candidate VALUES "
        "('method_b', 'run1', 13776, 5.5, 7.5, 0.8, 5.2, 0.7, 0.2, 0.7, now())"
    )

    # Seed month assignments for method_a (just 2 for testing)
    conn.execute(
        "INSERT INTO mart_calendar_candidate_month_image VALUES "
        "('run1', 'method_a', 1, 'December 2026', 13775, 0.8, 0.7)"
    )
    conn.execute(
        "INSERT INTO mart_calendar_candidate_month_image VALUES "
        "('run1', 'method_a', 2, 'January 2027', 13776, 0.6, 0.85)"
    )

    yield conn
    conn.close()


@pytest.fixture()
def client(db):
    """TestClient with in-memory DB injected."""
    app = create_app()
    app.state.db = db
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestImagesEndpoints:
    def test_list_images(self, client):
        r = client.get("/api/images")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert len(data["items"]) == 5

    def test_list_images_pagination(self, client):
        r = client.get("/api/images?per_page=2&page=1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert data["pages"] == 3
        assert len(data["items"]) == 2

    def test_list_images_sort_brightness(self, client):
        r = client.get("/api/images?sort=brightness")
        assert r.status_code == 200
        data = r.json()
        scores = [i["brightness_score"] for i in data["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_list_images_filter_cluster(self, client):
        r = client.get("/api/images?cluster_id=0")
        assert r.status_code == 200
        data = r.json()
        assert all(i["cluster_id"] == 0 for i in data["items"])

    def test_list_images_filter_min_score(self, client):
        r = client.get("/api/images?min_score=0.7")
        assert r.status_code == 200
        data = r.json()
        assert all(i["preference_score"] >= 0.7 for i in data["items"])

    def test_get_image_detail(self, client):
        r = client.get("/api/images/13775")
        assert r.status_code == 200
        data = r.json()
        assert data["image_sk"] == 13775
        assert data["source_image_id"] == "GUID0000"
        assert data["rank"] is not None
        assert data["candidates"] == ["method_a"]

    def test_get_image_not_found(self, client):
        r = client.get("/api/images/99999")
        assert r.status_code == 404


class TestCandidatesEndpoints:
    def test_list_candidates(self, client):
        r = client.get("/api/candidates")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        names = {c["candidate_name"] for c in data}
        assert names == {"method_a", "method_b"}

    def test_get_candidate_detail(self, client):
        r = client.get("/api/candidates/method_a")
        assert r.status_code == 200
        data = r.json()
        assert data["candidate"]["candidate_name"] == "method_a"
        assert len(data["images"]) == 2
        assert data["images"][0]["month_label"] == "December 2026"

    def test_get_candidate_not_found(self, client):
        r = client.get("/api/candidates/nonexistent")
        assert r.status_code == 404
