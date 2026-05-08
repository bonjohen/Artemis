"""Tests for S4 calendar optimization validation."""

import duckdb
import numpy as np
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """In-memory DuckDB with migrations, synthetic data, scores, clusters, embeddings, and candidates."""
    c = duckdb.connect(":memory:")
    apply_migrations(c, migrations_dir=MIGRATIONS_DIR)

    # Insert test images
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
    c.execute(
        """INSERT INTO stg_category
           (load_run_id, category_key, category_slug, category_label, image_count, showcase_guid)
           VALUES ('test', 'test', 'test', 'Test', 100, 'ART002-E-10000')"""
    )

    # Generate synthetic votes
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    generate_synthetic_votes(
        c,
        seed=42,
        voter_count=20,
        ballot_count=10,
        pair_count=40,
        ranking_count=5,
    )

    # Insert visual clusters and CLIP embeddings for all images
    image_sks = [r[0] for r in c.execute("SELECT image_sk FROM dim_image WHERE vote_pool_flag = true").fetchall()]
    rng = np.random.RandomState(42)
    for idx, sk in enumerate(image_sks):
        cluster_id = idx % 5
        c.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_type, cluster_algorithm, cluster_id, cluster_label, cluster_run_id)
               VALUES (?, 'visual', 'kmeans', ?, ?, 'test-run')""",
            [sk, cluster_id, str(cluster_id)],
        )
        # Insert a fake 8-dim CLIP embedding
        embedding = rng.randn(8).tolist()
        c.execute(
            """INSERT INTO feature_image_embedding
               (image_sk, embedding_model, embedding_model_version, embedding_vector, embedding_dimension)
               VALUES (?, 'test-clip', '1.0', ?::FLOAT[], 8)""",
            [sk, embedding],
        )

    # Compute preference scores
    from artemis_calendar.models import compute_preference_scores

    compute_preference_scores(c)

    # Create two fake candidate calendars (method_a and method_b)
    # Pick 13 images for each — method_a takes first 13, method_b takes a mix
    run_id = "test-opt-run"
    c.execute(
        """INSERT INTO mart_calendar_candidate
           (candidate_run_id, candidate_name, cover_image_sk,
            objective_score, popularity_score, diversity_score,
            month_fit_score, cover_fit_score, redundancy_penalty, uncertainty_penalty)
           VALUES (?, 'method_a', ?, 10.0, 3.0, 0.7, 0.5, 0.3, 0.1, 0.05)""",
        [run_id, image_sks[0]],
    )
    c.execute(
        """INSERT INTO mart_calendar_candidate
           (candidate_run_id, candidate_name, cover_image_sk,
            objective_score, popularity_score, diversity_score,
            month_fit_score, cover_fit_score, redundancy_penalty, uncertainty_penalty)
           VALUES (?, 'method_b', ?, 12.0, 3.5, 0.9, 0.6, 0.4, 0.05, 0.03)""",
        [run_id, image_sks[5]],
    )

    months = [
        "December 2026",
        "January 2027",
        "February 2027",
        "March 2027",
        "April 2027",
        "May 2027",
        "June 2027",
        "July 2027",
        "August 2027",
        "September 2027",
        "October 2027",
        "November 2027",
        "December 2027",
    ]

    for seq, month in enumerate(months):
        # method_a: first 13 images
        c.execute(
            """INSERT INTO mart_calendar_candidate_month_image
               (candidate_run_id, candidate_name, sequence_number, month_label,
                image_sk, month_fit_score, preference_score)
               VALUES (?, 'method_a', ?, ?, ?, 0.5, 0.5)""",
            [run_id, seq, month, image_sks[seq]],
        )
        # method_b: images spread across clusters (every 7th)
        b_idx = (seq * 7) % len(image_sks)
        c.execute(
            """INSERT INTO mart_calendar_candidate_month_image
               (candidate_run_id, candidate_name, sequence_number, month_label,
                image_sk, month_fit_score, preference_score)
               VALUES (?, 'method_b', ?, ?, ?, 0.6, 0.55)""",
            [run_id, seq, month, image_sks[b_idx]],
        )

    yield c
    c.close()


def test_compute_ground_truth_recovery(conn):
    from artemis_calendar.validate.calendar_validation import compute_ground_truth_recovery

    recovery = compute_ground_truth_recovery(conn)

    assert "method_a" in recovery
    assert "method_b" in recovery

    for _name, rec in recovery.items():
        assert "gt_cover_recovered" in rec
        assert "gt_month_recovered" in rec
        assert "gt_month_total" in rec
        assert "gt_recovery_rate" in rec
        assert 0 <= rec["gt_month_recovered"] <= rec["gt_month_total"]
        assert 0.0 <= rec["gt_recovery_rate"] <= 1.0


def test_compute_slate_diversity(conn):
    from artemis_calendar.validate.calendar_validation import compute_slate_diversity

    diversity = compute_slate_diversity(conn)

    assert "method_a" in diversity
    assert "method_b" in diversity

    for _name, div in diversity.items():
        assert div["slate_cluster_count"] > 0
        assert div["slate_max_cosine_sim"] is not None
        assert -1.0 <= div["slate_max_cosine_sim"] <= 1.0

    # method_b (spread every 7th) should have more cluster diversity than method_a (first 13)
    assert diversity["method_b"]["slate_cluster_count"] >= diversity["method_a"]["slate_cluster_count"]


def test_run_calendar_validation_orchestrator(conn):
    from artemis_calendar.validate.calendar_validation import run_calendar_validation

    report = run_calendar_validation(conn)

    assert "validation_run_id" in report
    assert report["validation_run_id"] is not None
    assert "methods" in report
    assert len(report["methods"]) == 2

    # Verify persisted
    rows = conn.execute("SELECT count(*) FROM mart_calendar_validation").fetchone()[0]
    assert rows == 2

    # Each method should have all expected fields
    for _name, m in report["methods"].items():
        assert "gt_recovery_rate" in m
        assert "slate_cluster_count" in m
        assert "objective_score" in m


def test_run_calendar_validation_idempotent(conn):
    from artemis_calendar.validate.calendar_validation import run_calendar_validation

    report1 = run_calendar_validation(conn)
    report2 = run_calendar_validation(conn)

    # Should have 4 rows (2 methods × 2 runs)
    rows = conn.execute("SELECT count(*) FROM mart_calendar_validation").fetchone()[0]
    assert rows == 4
    assert report1["validation_run_id"] != report2["validation_run_id"]
