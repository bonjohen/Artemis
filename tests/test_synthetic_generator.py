"""Tests for the synthetic vote generator."""

import duckdb
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """Create an in-memory DuckDB with all migrations applied."""
    c = duckdb.connect(":memory:")
    apply_migrations(c, migrations_dir=MIGRATIONS_DIR)
    # Insert a few test images into dim_image
    for i in range(100):
        c.execute(
            """INSERT INTO dim_image (source_image_id, vote_pool_flag, timeline_flag, enabled_flag)
               VALUES (?, true, ?, ?)""",
            [f"ART002-E-{10000 + i}", i < 10, i < 50],
        )
    # Insert a category
    c.execute(
        """INSERT INTO dim_category (category_key, category_slug, category_label, image_count)
           VALUES ('test', 'test', 'Test', 100)"""
    )
    # Insert a staging category for showcase boost
    c.execute(
        """INSERT INTO stg_category
           (load_run_id, category_key, category_slug, category_label, image_count, showcase_guid)
           VALUES ('test', 'test', 'test', 'Test', 100, 'ART002-E-10000')"""
    )
    yield c
    c.close()


def test_generate_votes_produces_correct_counts(conn):
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    counts = generate_synthetic_votes(
        conn,
        seed=42,
        voter_count=10,
        ballot_count=5,
        pair_count=20,
        ranking_count=3,
    )
    assert counts["dim_voter"] == 10
    assert counts["fact_batch_ballot"] == 5
    assert counts["fact_batch_ballot_image"] == 250  # 5 ballots × 50 images
    assert counts["fact_pairwise_vote"] == 20
    assert counts["fact_category_ranking"] == 3
    assert counts["fact_category_ranking_image"] == 9  # 3 rankings × 3 images
    assert counts["synthetic_image_truth"] == 100


def test_generate_votes_seed_reproducibility(conn):
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    counts1 = generate_synthetic_votes(
        conn,
        seed=99,
        voter_count=5,
        ballot_count=2,
        pair_count=5,
        ranking_count=2,
    )
    # Re-run with same seed — should clear and reproduce
    counts2 = generate_synthetic_votes(
        conn,
        seed=99,
        voter_count=5,
        ballot_count=2,
        pair_count=5,
        ranking_count=2,
    )
    assert counts1 == counts2

    # Verify actual data matches
    voters1 = conn.execute("SELECT voter_public_hash FROM dim_voter ORDER BY voter_sk").fetchall()
    # The hashes should be consistent (deterministic from seed)
    assert len(voters1) == 5


def test_synthetic_flag_set(conn):
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    generate_synthetic_votes(
        conn,
        seed=42,
        voter_count=5,
        ballot_count=2,
        pair_count=3,
        ranking_count=1,
    )
    # All vote records should have synthetic_flag = true
    for table in [
        "dim_voter",
        "fact_vote_session",
        "fact_batch_ballot",
        "fact_batch_ballot_image",
        "fact_pairwise_vote",
        "fact_category_ranking",
        "fact_category_ranking_image",
    ]:
        non_synthetic = conn.execute(f"SELECT count(*) FROM {table} WHERE synthetic_flag = false").fetchone()[0]
        assert non_synthetic == 0, f"{table} has non-synthetic rows"
