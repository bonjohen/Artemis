"""Tests for voting block vote generator."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from artemis_calendar.synthetic.block_generator import (
    compute_attribute_match,
    compute_block_utility,
    generate_block_votes,
)
from artemis_calendar.vision.voting_config import (
    PreferenceRule,
    VotingBlockConfig,
    VotingScenarioConfig,
)


def _make_block(
    block_id: str = "test",
    all_of: list[str] | None = None,
    none_of: list[str] | None = None,
    preference_weight: float = 2.0,
    randomness_weight: float = 0.3,
) -> VotingBlockConfig:
    return VotingBlockConfig(
        block_id=block_id,
        label=f"Test {block_id}",
        voter_count=5,
        votes_per_voter=10,
        preference_rules=PreferenceRule(
            all_of=all_of or [],
            none_of=none_of or [],
        ),
        preference_weight=preference_weight,
        randomness_weight=randomness_weight,
    )


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())
    return conn


@pytest.fixture
def db_with_data(db) -> duckdb.DuckDBPyConnection:
    """DB with 50 images and some attributes."""
    for i in range(1, 51):
        db.execute(
            """INSERT INTO dim_image
               (image_sk, source_image_id, vote_pool_flag)
               VALUES (?, ?, true)""",
            [i, f"img_{i:03d}"],
        )

    # Images 1-15: earth + moon
    for i in range(1, 16):
        for code in ("earth", "moon"):
            db.execute(
                """INSERT INTO feature_image_attribute
                   (image_sk, attribute_code, confidence_score,
                    classification, label_source, is_accepted)
                   VALUES (?, ?, 0.90, 'accepted', 'test', true)""",
                [i, code],
            )

    # Images 16-30: earth only
    for i in range(16, 31):
        db.execute(
            """INSERT INTO feature_image_attribute
               (image_sk, attribute_code, confidence_score,
                classification, label_source, is_accepted)
               VALUES (?, 'earth', 0.90, 'accepted', 'test', true)""",
            [i],
        )

    # Images 31-50: no attributes
    return db


@pytest.fixture
def small_config() -> VotingScenarioConfig:
    return VotingScenarioConfig(
        scenario_id="test_scenario",
        scenario_name="Test Scenario",
        description="Small test",
        seed=42,
        blocks=[
            _make_block("biased", all_of=["earth", "moon"]),
            _make_block(
                "neutral", preference_weight=0.0, randomness_weight=1.0
            ),
        ],
    )


class TestAttributeMatch:
    def test_full_match(self):
        block = _make_block(all_of=["earth", "moon"])
        score = compute_attribute_match({"earth", "moon", "sun"}, block)
        assert score == 1.0

    def test_partial_match(self):
        block = _make_block(all_of=["earth", "moon"])
        score = compute_attribute_match({"earth"}, block)
        assert 0.0 < score < 1.0

    def test_no_match(self):
        block = _make_block(all_of=["earth", "moon"])
        score = compute_attribute_match({"sun"}, block)
        assert score == 0.0

    def test_neutral_block(self):
        block = _make_block(preference_weight=0.0)
        score = compute_attribute_match({"earth", "moon"}, block)
        assert score == 0.0

    def test_none_of_penalty(self):
        block = _make_block(all_of=["earth"], none_of=["moon"])
        score_clean = compute_attribute_match({"earth"}, block)
        score_dirty = compute_attribute_match({"earth", "moon"}, block)
        assert score_clean > score_dirty


class TestBlockUtility:
    def test_biased_prefers_matching(self):
        import random

        block = _make_block(all_of=["earth", "moon"], preference_weight=3.0, randomness_weight=0.0)
        rng = random.Random(42)

        u_match = compute_block_utility({"earth", "moon"}, block, 0.5, rng)
        u_no = compute_block_utility(set(), block, 0.5, rng)
        assert u_match > u_no

    def test_seed_reproducible(self):
        import random

        block = _make_block(all_of=["earth"])
        rng1 = random.Random(99)
        rng2 = random.Random(99)
        u1 = compute_block_utility({"earth"}, block, 0.5, rng1)
        u2 = compute_block_utility({"earth"}, block, 0.5, rng2)
        assert u1 == u2


class TestGenerateBlockVotes:
    def test_generates_votes(self, db_with_data, small_config):
        summary = generate_block_votes(db_with_data, small_config)
        assert summary["total_voters"] == 10  # 5 + 5
        assert summary["total_ballots"] == 100  # 10 voters * 10 votes each
        assert summary["total_ballot_images"] > 0

    def test_voter_block_assignment(self, db_with_data, small_config):
        generate_block_votes(db_with_data, small_config)

        assignments = db_with_data.execute(
            """SELECT block_id, count(*) FROM synthetic_voter_block_assignment
               WHERE scenario_id = 'test_scenario'
               GROUP BY block_id"""
        ).fetchall()
        assign_map = {r[0]: r[1] for r in assignments}
        assert assign_map["biased"] == 5
        assert assign_map["neutral"] == 5

    def test_biased_block_selects_matching(self, db_with_data, small_config):
        generate_block_votes(db_with_data, small_config)

        # Get selections by biased block voters
        biased_selections = db_with_data.execute(
            """SELECT bbi.image_sk, count(*) as cnt
               FROM fact_batch_ballot_image bbi
               JOIN synthetic_voter_block_assignment sva
                   ON bbi.voter_sk = sva.voter_sk
               WHERE sva.block_id = 'biased' AND bbi.was_selected = true
               GROUP BY bbi.image_sk
               ORDER BY cnt DESC
               LIMIT 10"""
        ).fetchall()

        # Top selected images should mostly be from earth+moon set (1-15)
        top_sks = [r[0] for r in biased_selections[:5]]
        earth_moon_count = sum(1 for sk in top_sks if sk <= 15)
        assert earth_moon_count >= 3  # At least 3 of top 5 should match

    def test_output_summary_json(self, db_with_data, small_config):
        summary = generate_block_votes(db_with_data, small_config)
        assert "output_path" in summary
        assert len(summary["blocks"]) == 2
        for b in summary["blocks"]:
            assert "top_selected_images" in b
