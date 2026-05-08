"""Acceptance tests for the biased voting blocks pipeline.

End-to-end: config -> generate -> analyze -> export -> verify.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from artemis_calendar.models.block_stats import run_block_analysis
from artemis_calendar.static.exporter import export_all_static_json
from artemis_calendar.synthetic.block_generator import generate_block_votes
from artemis_calendar.vision.attributes import load_attribute_vocabulary
from artemis_calendar.vision.loader import seed_attribute_vocabulary
from artemis_calendar.vision.voting_config import (
    PreferenceRule,
    VotingBlockConfig,
    VotingScenarioConfig,
    dry_run,
    load_voting_config,
    validate_voting_config,
)


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())
    return conn


@pytest.fixture
def full_pipeline_db(db) -> tuple[duckdb.DuckDBPyConnection, str]:
    """Full end-to-end: images, attributes, clusters, block votes, analysis."""
    load_attribute_vocabulary()  # validate config loads
    seed_attribute_vocabulary(db)

    # 100 images
    for i in range(1, 101):
        db.execute(
            """INSERT INTO dim_image
               (image_sk, source_image_id, vote_pool_flag)
               VALUES (?, ?, true)""",
            [i, f"img_{i:04d}"],
        )

    # Earth+Moon images: 1-25
    for i in range(1, 26):
        for code in ("earth", "moon"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score,
                    classification, label_source, is_accepted)
                   VALUES (?, ?, 0.92, 'accepted', 'vision_model', true)""",
                [i, code],
            )
        # Also add earth_and_moon derived
        db.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score,
                classification, label_source, is_accepted)
               VALUES (?, 'earth_and_moon', 1.0, 'accepted', 'derived_rule', true)""",
            [i],
        )

    # Earth-only images: 26-50
    for i in range(26, 51):
        db.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score,
                classification, label_source, is_accepted)
               VALUES (?, 'earth', 0.90, 'accepted', 'vision_model', true)""",
            [i],
        )

    # Moon+Sun images: 51-60
    for i in range(51, 61):
        for code in ("moon", "sun"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score,
                    classification, label_source, is_accepted)
                   VALUES (?, ?, 0.88, 'accepted', 'vision_model', true)""",
                [i, code],
            )

    # No attributes: 61-100

    # Simple clusters
    for i in range(1, 101):
        db.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_run_id, cluster_type, cluster_algorithm,
                cluster_id, distance_to_centroid)
               VALUES (?, 'run1', 'visual', 'kmeans', ?, 0.5)""",
            [i, i % 5],
        )

    # Use a scaled-down version of the real config for speed
    config = VotingScenarioConfig(
        scenario_id="earth_moon_bias_test",
        scenario_name="Earth / Moon / Sun Bias Test",
        description="Acceptance test (scaled down)",
        seed=42,
        blocks=[
            VotingBlockConfig(
                block_id="earth_moon_block",
                label="Earth and Moon Preference Block",
                voter_count=5, votes_per_voter=10,
                preference_rules=PreferenceRule(all_of=["earth", "moon"]),
                preference_weight=2.5, randomness_weight=0.35,
            ),
            VotingBlockConfig(
                block_id="earth_only_block",
                label="Earth-Only Preference Block",
                voter_count=4, votes_per_voter=10,
                preference_rules=PreferenceRule(
                    all_of=["earth"], none_of=["moon", "sun"]
                ),
                preference_weight=2.2, randomness_weight=0.40,
            ),
            VotingBlockConfig(
                block_id="moon_sun_block",
                label="Moon and Sun Preference Block",
                voter_count=6, votes_per_voter=10,
                preference_rules=PreferenceRule(all_of=["moon", "sun"]),
                preference_weight=2.6, randomness_weight=0.30,
            ),
            VotingBlockConfig(
                block_id="neutral_control",
                label="Neutral Control Voters",
                voter_count=10, votes_per_voter=10,
                preference_rules=PreferenceRule(),
                preference_weight=0.0, randomness_weight=1.0,
            ),
        ],
    )

    # Generate block votes
    generate_block_votes(db, config)

    # Run analysis
    run_block_analysis(db, config.scenario_id)

    return db, config.scenario_id


class TestConfigValidation:
    def test_real_config_valid(self):
        config_path = (
            Path(__file__).parent.parent
            / "config" / "voting_blocks" / "earth_moon_bias_test.yaml"
        )
        config = load_voting_config(config_path)
        errors = validate_voting_config(config)
        assert errors == []

    def test_expected_voter_counts(self):
        config_path = (
            Path(__file__).parent.parent
            / "config" / "voting_blocks" / "earth_moon_bias_test.yaml"
        )
        config = load_voting_config(config_path)
        assert config.total_voters == 125  # Full config
        assert config.total_votes == 5000  # Full config


class TestVoterGeneration:
    def test_voter_counts_per_block(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        assignments = conn.execute(
            """SELECT block_id, count(*) FROM synthetic_voter_block_assignment
               WHERE scenario_id = ?
               GROUP BY block_id""",
            [scenario_id],
        ).fetchall()
        assign_map = {r[0]: r[1] for r in assignments}
        assert assign_map["earth_moon_block"] == 5
        assert assign_map["earth_only_block"] == 4
        assert assign_map["moon_sun_block"] == 6
        assert assign_map["neutral_control"] == 10

    def test_vote_counts_generated(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        ballot_count = conn.execute(
            "SELECT count(*) FROM fact_batch_ballot WHERE synthetic_flag = true"
        ).fetchone()[0]
        assert ballot_count == 250  # 25 voters * 10 votes each


class TestBiasDetection:
    def test_attribute_lift_measurable(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        lifts = conn.execute(
            """SELECT block_id, attribute_code, lift
               FROM mart_voting_block_attribute_lift
               WHERE scenario_id = ? AND lift > 1.0""",
            [scenario_id],
        ).fetchall()
        # Biased blocks should produce measurable lift
        assert len(lifts) > 0

        # Earth+moon block should have lift for earth
        em_lifts = [r for r in lifts if r[0] == "earth_moon_block" and r[1] == "earth"]
        assert len(em_lifts) > 0
        assert em_lifts[0][2] > 1.0

    def test_cluster_lift_calculated(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        count = conn.execute(
            "SELECT count(*) FROM mart_voting_block_cluster_lift WHERE scenario_id = ?",
            [scenario_id],
        ).fetchone()[0]
        assert count > 0

    def test_score_impact_calculated(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        count = conn.execute(
            "SELECT count(*) FROM mart_voting_block_score_impact WHERE scenario_id = ?",
            [scenario_id],
        ).fetchone()[0]
        assert count > 0

        # Check that deltas exist
        deltas = conn.execute(
            """SELECT block_id, count(*) FROM mart_voting_block_score_impact
               WHERE scenario_id = ? AND score_delta != 0
               GROUP BY block_id""",
            [scenario_id],
        ).fetchall()
        assert len(deltas) > 0

    def test_detection_status_assigned(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        statuses = conn.execute(
            """SELECT block_id, detection_status
               FROM mart_voting_block_summary
               WHERE scenario_id = ?""",
            [scenario_id],
        ).fetchall()
        status_map = {r[0]: r[1] for r in statuses}
        assert len(status_map) == 4
        # Neutral should be not_applicable
        assert status_map["neutral_control"] == "not_applicable"


class TestStaticExport:
    def test_json_files_generated(self, full_pipeline_db, tmp_path):
        conn, scenario_id = full_pipeline_db
        paths = export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        for name, path in paths.items():
            assert Path(path).exists(), f"{name} not at {path}"

    def test_no_admin_controls(self, full_pipeline_db, tmp_path):
        conn, scenario_id = full_pipeline_db
        paths = export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        for _name, path in paths.items():
            content = Path(path).read_text()
            assert "voter_sk" not in content
            assert "voter_public_hash" not in content
            assert "random_seed" not in content
            assert "model_prompt" not in content
            assert "C:\\" not in content  # No local paths

    def test_summary_has_correct_structure(self, full_pipeline_db, tmp_path):
        conn, scenario_id = full_pipeline_db
        export_all_static_json(conn, scenario_id, output_dir=tmp_path)

        data = json.loads(
            (tmp_path / "voting-block-summary.json").read_text()
        )
        assert data["block_count"] == 4
        assert data["total_voters"] == 25


class TestDryRun:
    def test_dry_run_image_counts(self, full_pipeline_db):
        conn, scenario_id = full_pipeline_db
        config_path = (
            Path(__file__).parent.parent
            / "config" / "voting_blocks" / "earth_moon_bias_test.yaml"
        )
        config = load_voting_config(config_path)
        result = dry_run(config, conn)

        block_map = {b.block_id: b for b in result.blocks}

        # Earth+Moon: images 1-25
        assert block_map["earth_moon_block"].matching_images == 25

        # Earth-only: images 26-50 (earth but NOT moon, NOT sun)
        assert block_map["earth_only_block"].matching_images == 25

        # Moon+Sun: images 51-60
        assert block_map["moon_sun_block"].matching_images == 10

        # Neutral: all 100
        assert block_map["neutral_control"].matching_images == 100
