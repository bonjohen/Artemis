"""Tests for vision cluster labeling and review export."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from artemis_calendar.vision.cluster_labels import (
    _generate_label,
    export_cluster_review,
    label_clusters,
)


@pytest.fixture
def db():
    """In-memory DuckDB with all migrations applied and test data."""
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())

    # Create test images
    for i in range(1, 21):
        conn.execute(
            """INSERT INTO dim_image (image_sk, source_image_id, vote_pool_flag, thumb_downloaded)
               VALUES (?, ?, true, true)""",
            [i, f"img_{i:03d}"],
        )

    # Create cluster assignments — 2 clusters of 10 images each
    run_id = "test-run-001"
    for i in range(1, 21):
        cluster_id = 0 if i <= 10 else 1
        distance = abs(i - (5 if cluster_id == 0 else 15)) * 0.1
        conn.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_run_id, cluster_type, cluster_algorithm, cluster_id, distance_to_centroid)
               VALUES (?, ?, 'visual', 'kmeans', ?, ?)""",
            [i, run_id, cluster_id, distance],
        )

    # Create attribute labels for images
    # Cluster 0: mostly earth + deep_space
    for i in range(1, 11):
        conn.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification, label_source, run_id, is_accepted)
               VALUES (?, 'earth', 0.92, 'accepted', 'vision_model', 'attr-run', true)""",
            [i],
        )
        conn.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification, label_source, run_id, is_accepted)
               VALUES (?, 'deep_space', 0.88, 'accepted', 'vision_model', 'attr-run', true)""",
            [i],
        )

    # Cluster 1: mostly moon + astronaut
    for i in range(11, 21):
        conn.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification, label_source, run_id, is_accepted)
               VALUES (?, 'moon', 0.90, 'accepted', 'vision_model', 'attr-run', true)""",
            [i],
        )
        conn.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification, label_source, run_id, is_accepted)
               VALUES (?, 'astronaut', 0.85, 'accepted', 'vision_model', 'attr-run', true)""",
            [i],
        )

    return conn


class TestGenerateLabel:
    def test_single_attribute(self):
        attrs = [{"code": "earth", "count": 10, "avg_confidence": 0.9}]
        assert _generate_label(attrs) == "Earth"

    def test_two_attributes(self):
        attrs = [
            {"code": "earth", "count": 10, "avg_confidence": 0.9},
            {"code": "moon", "count": 8, "avg_confidence": 0.85},
        ]
        assert _generate_label(attrs) == "Earth and Moon"

    def test_three_attributes(self):
        attrs = [
            {"code": "deep_space", "count": 10, "avg_confidence": 0.9},
            {"code": "earth", "count": 8, "avg_confidence": 0.85},
            {"code": "moon", "count": 5, "avg_confidence": 0.8},
        ]
        assert _generate_label(attrs) == "Deep Space, Earth, and Moon"

    def test_empty(self):
        assert _generate_label([]) == "Uncategorized"

    def test_underscore_handling(self):
        attrs = [{"code": "deep_space", "count": 10, "avg_confidence": 0.9}]
        assert _generate_label(attrs) == "Deep Space"


class TestLabelClusters:
    def test_labels_assigned(self, db):
        count = label_clusters(db, cluster_run_id="test-run-001", cluster_type="visual")
        assert count == 2

        # Check labels were written
        labels = db.execute(
            """SELECT DISTINCT cluster_label FROM feature_image_cluster
               WHERE cluster_run_id = 'test-run-001' AND cluster_type = 'visual'
               ORDER BY cluster_label"""
        ).fetchall()
        assert len(labels) == 2
        # Cluster 0 should have earth/deep_space label
        all_labels = [r[0] for r in labels]
        assert any("Earth" in lbl for lbl in all_labels)
        assert any("Moon" in lbl for lbl in all_labels)

    def test_no_clusters_returns_zero(self, db):
        count = label_clusters(db, cluster_run_id="nonexistent", cluster_type="visual")
        assert count == 0

    def test_auto_detect_latest_run(self, db):
        count = label_clusters(db, cluster_type="visual")
        assert count == 2


class TestExportClusterReview:
    def test_json_export(self, db, tmp_path):
        label_clusters(db, cluster_run_id="test-run-001")
        result = export_cluster_review(
            db, cluster_run_id="test-run-001", output_dir=tmp_path
        )
        assert result["cluster_count"] == 2

        json_path = Path(result["json_path"])
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["cluster_count"] == 2
        assert len(data["clusters"]) == 2
        for c in data["clusters"]:
            assert "dominant_attributes" in c
            assert "representative_images" in c
            assert "outlier_images" in c

    def test_md_export(self, db, tmp_path):
        label_clusters(db, cluster_run_id="test-run-001")
        result = export_cluster_review(
            db, cluster_run_id="test-run-001", output_dir=tmp_path
        )
        md_path = Path(result["md_path"])
        assert md_path.exists()
        content = md_path.read_text()
        assert "Cluster Review" in content
        assert "Dominant attributes" in content
        assert "Representative images" in content
