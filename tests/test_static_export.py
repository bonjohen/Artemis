"""Tests for static JSON export."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from artemis_calendar.models.block_stats import run_block_analysis
from artemis_calendar.static.exporter import export_all_static_json
from artemis_calendar.synthetic.block_generator import generate_block_votes
from artemis_calendar.vision.voting_config import (
    PreferenceRule,
    VotingBlockConfig,
    VotingScenarioConfig,
)


@pytest.fixture
def populated_db(tmp_path) -> tuple[duckdb.DuckDBPyConnection, str]:
    """Full pipeline: images, attributes, clusters, votes, analysis."""
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())

    # 30 images with attributes and clusters
    for i in range(1, 31):
        conn.execute(
            "INSERT INTO dim_image (image_sk, source_image_id, vote_pool_flag) VALUES (?, ?, true)",
            [i, f"img_{i:03d}"],
        )
    for i in range(1, 11):
        for code in ("earth", "moon"):
            conn.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score,
                    classification, label_source, is_accepted)
                   VALUES (?, ?, 0.92, 'accepted', 'test', true)""",
                [i, code],
            )
    for i in range(1, 31):
        conn.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_run_id, cluster_type, cluster_algorithm,
                cluster_id, distance_to_centroid)
               VALUES (?, 'r1', 'visual', 'kmeans', ?, 0.5)""",
            [i, i % 3],
        )

    config = VotingScenarioConfig(
        scenario_id="export_test",
        scenario_name="Export Test",
        description="Test",
        seed=42,
        blocks=[
            VotingBlockConfig(
                block_id="biased", label="Biased",
                voter_count=5, votes_per_voter=10,
                preference_rules=PreferenceRule(all_of=["earth"]),
                preference_weight=2.0, randomness_weight=0.3,
            ),
            VotingBlockConfig(
                block_id="neutral", label="Neutral",
                voter_count=5, votes_per_voter=10,
                preference_rules=PreferenceRule(),
                preference_weight=0.0, randomness_weight=1.0,
            ),
        ],
    )
    generate_block_votes(conn, config)
    run_block_analysis(conn, "export_test")

    return conn, "export_test"


class TestExportAll:
    def test_exports_all_files(self, populated_db, tmp_path):
        conn, scenario_id = populated_db
        paths = export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        assert "voting_block_summary" in paths
        assert "attribute_lift" in paths
        assert "cluster_lift" in paths
        assert "score_impact" in paths
        assert "calendar_impact" in paths

        # All files exist
        for name, path in paths.items():
            assert Path(path).exists(), f"{name} not found at {path}"

    def test_voting_block_summary_schema(self, populated_db, tmp_path):
        conn, scenario_id = populated_db
        export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        data = json.loads((tmp_path / "voting-block-summary.json").read_text())
        assert data["scenario_id"] == "export_test"
        assert data["block_count"] == 2
        assert len(data["blocks"]) == 2

        for block in data["blocks"]:
            assert "block_id" in block
            assert "label" in block
            assert "voter_count" in block
            assert "detection_status" in block

    def test_attribute_lift_schema(self, populated_db, tmp_path):
        conn, scenario_id = populated_db
        export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        data = json.loads(
            (tmp_path / "voting-block-attribute-lift.json").read_text()
        )
        assert isinstance(data, list)
        if data:
            assert "block_id" in data[0]
            assert "lift" in data[0]
            assert "ci_low" in data[0]

    def test_no_pii_in_exports(self, populated_db, tmp_path):
        conn, scenario_id = populated_db
        paths = export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        for name, path in paths.items():
            content = Path(path).read_text()
            assert "voter_sk" not in content, f"PII in {name}"
            assert "voter_public_hash" not in content, f"PII in {name}"
            assert "random_seed" not in content, f"PII in {name}"

    def test_calendar_impact_schema(self, populated_db, tmp_path):
        conn, scenario_id = populated_db
        export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        data = json.loads(
            (tmp_path / "voting-block-calendar-impact.json").read_text()
        )
        assert data["scenario_id"] == "export_test"
        assert "changed_month_count" in data
