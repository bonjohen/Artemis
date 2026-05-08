"""Tests for block-aware statistical analysis."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from artemis_calendar.models.block_stats import (
    compute_attribute_lift,
    compute_block_similarity,
    compute_calendar_impact,
    compute_detection_status,
    compute_score_impact,
    run_block_analysis,
)
from artemis_calendar.synthetic.block_generator import generate_block_votes
from artemis_calendar.vision.voting_config import (
    PreferenceRule,
    VotingBlockConfig,
    VotingScenarioConfig,
)


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())
    return conn


@pytest.fixture
def populated_db(db) -> tuple[duckdb.DuckDBPyConnection, str]:
    """DB with images, attributes, clusters, and generated block votes."""
    # Create 50 images
    for i in range(1, 51):
        db.execute(
            "INSERT INTO dim_image (image_sk, source_image_id, vote_pool_flag) VALUES (?, ?, true)",
            [i, f"img_{i:03d}"],
        )

    # Attributes: images 1-15 have earth+moon, 16-30 earth only, 31-50 none
    for i in range(1, 16):
        for code in ("earth", "moon"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score, classification,
                    label_source, is_accepted)
                   VALUES (?, ?, 0.92, 'accepted', 'test', true)""",
                [i, code],
            )
    for i in range(16, 31):
        db.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification,
                label_source, is_accepted)
               VALUES (?, 'earth', 0.90, 'accepted', 'test', true)""",
            [i],
        )

    # Simple clusters: 2 clusters
    for i in range(1, 51):
        cluster_id = 0 if i <= 25 else 1
        db.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_run_id, cluster_type, cluster_algorithm,
                cluster_id, distance_to_centroid)
               VALUES (?, 'run1', 'visual', 'kmeans', ?, 0.5)""",
            [i, cluster_id],
        )

    # Generate block votes
    config = VotingScenarioConfig(
        scenario_id="test_stats",
        scenario_name="Stats Test",
        description="Test",
        seed=42,
        blocks=[
            VotingBlockConfig(
                block_id="biased",
                label="Earth+Moon Biased",
                voter_count=10,
                votes_per_voter=20,
                preference_rules=PreferenceRule(all_of=["earth", "moon"]),
                preference_weight=3.0,
                randomness_weight=0.2,
            ),
            VotingBlockConfig(
                block_id="neutral",
                label="Neutral",
                voter_count=10,
                votes_per_voter=20,
                preference_rules=PreferenceRule(),
                preference_weight=0.0,
                randomness_weight=1.0,
            ),
        ],
    )
    generate_block_votes(db, config)

    return db, "test_stats"


class TestAttributeLift:
    def test_biased_block_has_higher_lift(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_attribute_lift(conn, scenario_id)
        assert len(results) > 0

        # Biased block should have higher earth lift than neutral block
        biased_earth = [
            r for r in results
            if r["block_id"] == "biased" and r["attribute_code"] == "earth"
        ]
        neutral_earth = [
            r for r in results
            if r["block_id"] == "neutral" and r["attribute_code"] == "earth"
        ]
        assert len(biased_earth) == 1
        assert len(neutral_earth) == 1
        assert biased_earth[0]["lift"] >= neutral_earth[0]["lift"]

    def test_lift_has_confidence_intervals(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_attribute_lift(conn, scenario_id)
        for r in results:
            assert r["confidence_interval_low"] <= r["confidence_interval_high"]
            assert r["confidence_interval_low"] >= 0
            assert r["confidence_interval_high"] <= 1


class TestBlockSimilarity:
    def test_similarity_computed(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_block_similarity(conn, scenario_id)
        assert len(results) == 1  # 2 blocks = 1 pair

    def test_similarity_values_valid(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_block_similarity(conn, scenario_id)
        for r in results:
            assert 0 <= r["jaccard_top_n"] <= 1
            assert -1 <= r["cosine_similarity"] <= 1


class TestScoreImpact:
    def test_impact_computed(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_score_impact(conn, scenario_id)
        assert len(results) > 0

    def test_biased_promotes_matching(self, populated_db):
        conn, scenario_id = populated_db
        results = compute_score_impact(conn, scenario_id)

        # Get top promoted images by biased block
        biased = [r for r in results if r["block_id"] == "biased" and r["score_delta"] > 0]
        biased.sort(key=lambda x: -x["score_delta"])

        if biased:
            # Top promoted should be earth+moon images (sk 1-15)
            top_sk = biased[0]["image_sk"]
            assert top_sk <= 15


class TestCalendarImpact:
    def test_calendar_impact(self, populated_db):
        conn, scenario_id = populated_db
        result = compute_calendar_impact(conn, scenario_id)
        assert result["scenario_id"] == scenario_id
        assert result["cover_image_with"] is not None
        assert result["changed_month_count"] >= 0


class TestDetectionStatus:
    def test_detected(self):
        lift = [
            {"block_id": "b1", "attribute_code": "earth", "lift": 3.5},
            {"block_id": "b1", "attribute_code": "moon", "lift": 2.8},
        ]
        result = compute_detection_status(lift, {"b1": ["earth", "moon"]})
        assert result["b1"]["status"] == "detected"
        assert result["b1"]["strength"] > 2.0

    def test_not_detected(self):
        lift = [
            {"block_id": "b1", "attribute_code": "earth", "lift": 1.02},
        ]
        result = compute_detection_status(lift, {"b1": ["earth"]})
        assert result["b1"]["status"] == "not_detected"

    def test_neutral_block(self):
        result = compute_detection_status([], {"neutral": []})
        assert result["neutral"]["status"] == "not_applicable"


class TestRunBlockAnalysis:
    def test_full_analysis(self, populated_db):
        conn, scenario_id = populated_db
        result = run_block_analysis(conn, scenario_id)
        assert result["scenario_id"] == scenario_id
        assert result["counts"]["attribute_lift"] > 0
        assert result["counts"]["block_summary"] == 2

        # Verify data was written to marts
        attr_count = conn.execute(
            "SELECT count(*) FROM mart_voting_block_attribute_lift WHERE scenario_id = ?",
            [scenario_id],
        ).fetchone()[0]
        assert attr_count > 0

        summary_count = conn.execute(
            "SELECT count(*) FROM mart_voting_block_summary WHERE scenario_id = ?",
            [scenario_id],
        ).fetchone()[0]
        assert summary_count == 2
