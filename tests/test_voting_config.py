"""Tests for voting block config schema, validation, and dry-run."""

from __future__ import annotations

import textwrap
from pathlib import Path

import duckdb
import pytest

from artemis_calendar.vision.voting_config import (
    DryRunResult,
    VotingScenarioConfig,
    dry_run,
    load_voting_config,
    save_scenario_to_db,
    validate_voting_config,
)


@pytest.fixture
def real_config() -> VotingScenarioConfig:
    """Load the real earth_moon_bias_test.yaml config."""
    config_path = Path(__file__).parent.parent / "config" / "voting_blocks" / "earth_moon_bias_test.yaml"
    return load_voting_config(config_path)


@pytest.fixture
def bad_config(tmp_path: Path) -> Path:
    config = tmp_path / "bad.yaml"
    config.write_text(textwrap.dedent("""\
        scenario_id: bad_test
        scenario_name: Bad Test
        description: Invalid config
        seed: 42
        blocks:
          - block_id: dup_block
            label: Block A
            voter_count: 10
            votes_per_voter: 20
            preference_rules:
              all_of: [earth]
          - block_id: dup_block
            label: Block B
            voter_count: 5
            votes_per_voter: 20
            preference_rules:
              all_of: [mars_nonexistent]
          - block_id: contradiction
            label: Contradiction
            voter_count: 10
            votes_per_voter: 20
            preference_rules:
              all_of: [earth]
              none_of: [earth]
    """))
    return config


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())
    return conn


@pytest.fixture
def db_with_attrs(db) -> duckdb.DuckDBPyConnection:
    """DB with images and attribute data for dry-run testing."""
    # Create 20 images
    for i in range(1, 21):
        db.execute(
            """INSERT INTO dim_image (image_sk, source_image_id, vote_pool_flag)
               VALUES (?, ?, true)""",
            [i, f"img_{i:03d}"],
        )

    # Images 1-8: earth + moon
    for i in range(1, 9):
        for code in ("earth", "moon"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score, classification,
                    label_source, is_accepted)
                   VALUES (?, ?, 0.92, 'accepted', 'test', true)""",
                [i, code],
            )

    # Images 9-14: earth only (no moon, no sun)
    for i in range(9, 15):
        db.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score, classification,
                label_source, is_accepted)
               VALUES (?, 'earth', 0.90, 'accepted', 'test', true)""",
            [i],
        )

    # Images 15-17: moon + sun
    for i in range(15, 18):
        for code in ("moon", "sun"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score, classification,
                    label_source, is_accepted)
                   VALUES (?, ?, 0.88, 'accepted', 'test', true)""",
                [i, code],
            )

    # Images 18-20: no relevant attributes
    return db


class TestLoadConfig:
    def test_load_real_config(self, real_config: VotingScenarioConfig) -> None:
        assert real_config.scenario_id == "earth_moon_bias_test"
        assert len(real_config.blocks) == 4
        assert real_config.total_voters == 125
        assert real_config.total_votes == 5000

    def test_block_ids(self, real_config: VotingScenarioConfig) -> None:
        ids = [b.block_id for b in real_config.blocks]
        assert "earth_moon_block" in ids
        assert "earth_only_block" in ids
        assert "moon_sun_block" in ids
        assert "neutral_control" in ids

    def test_config_hash_deterministic(self, real_config: VotingScenarioConfig) -> None:
        h1 = real_config.config_hash
        h2 = real_config.config_hash
        assert h1 == h2
        assert len(h1) == 16


class TestValidation:
    def test_valid_config(self, real_config: VotingScenarioConfig) -> None:
        errors = validate_voting_config(real_config)
        assert errors == []

    def test_bad_config(self, bad_config: Path) -> None:
        config = load_voting_config(bad_config)
        errors = validate_voting_config(config)
        assert any("Duplicate block_id" in e for e in errors)
        assert any("mars_nonexistent" in e for e in errors)
        assert any("both all_of and none_of" in e for e in errors)


class TestDryRun:
    def test_dry_run_counts(
        self, real_config: VotingScenarioConfig, db_with_attrs: duckdb.DuckDBPyConnection
    ) -> None:
        result = dry_run(real_config, db_with_attrs)
        assert isinstance(result, DryRunResult)
        assert result.scenario_id == "earth_moon_bias_test"

        # Find each block's result
        block_map = {b.block_id: b for b in result.blocks}

        # earth_moon_block: images with BOTH earth AND moon = 8
        assert block_map["earth_moon_block"].matching_images == 8

        # earth_only_block: images with earth AND NOT moon AND NOT sun = 6 (images 9-14)
        assert block_map["earth_only_block"].matching_images == 6

        # moon_sun_block: images with BOTH moon AND sun = 3 (images 15-17)
        assert block_map["moon_sun_block"].matching_images == 3

        # neutral_control: no rules = all 20 images
        assert block_map["neutral_control"].matching_images == 20

    def test_low_count_warning(
        self, real_config: VotingScenarioConfig, db_with_attrs: duckdb.DuckDBPyConnection
    ) -> None:
        result = dry_run(real_config, db_with_attrs)
        block_map = {b.block_id: b for b in result.blocks}

        # moon_sun_block has 3 matching images but 40 votes_per_voter
        assert any("Low image count" in w for w in block_map["moon_sun_block"].warnings)


class TestSaveToDB:
    def test_save_and_read(
        self, real_config: VotingScenarioConfig, db: duckdb.DuckDBPyConnection
    ) -> None:
        save_scenario_to_db(db, real_config)

        # Check scenario
        row = db.execute(
            "SELECT scenario_name FROM dim_voting_scenario WHERE scenario_id = ?",
            [real_config.scenario_id],
        ).fetchone()
        assert row[0] == "Earth / Moon / Sun Bias Test"

        # Check blocks
        blocks = db.execute(
            "SELECT count(*) FROM dim_voting_block WHERE scenario_id = ?",
            [real_config.scenario_id],
        ).fetchone()[0]
        assert blocks == 4

        # Check rules
        rules = db.execute(
            "SELECT count(*) FROM voting_block_rule WHERE scenario_id = ?",
            [real_config.scenario_id],
        ).fetchone()[0]
        assert rules > 0

    def test_save_idempotent(
        self, real_config: VotingScenarioConfig, db: duckdb.DuckDBPyConnection
    ) -> None:
        save_scenario_to_db(db, real_config)
        save_scenario_to_db(db, real_config)  # Should not fail or duplicate

        blocks = db.execute(
            "SELECT count(*) FROM dim_voting_block WHERE scenario_id = ?",
            [real_config.scenario_id],
        ).fetchone()[0]
        assert blocks == 4
