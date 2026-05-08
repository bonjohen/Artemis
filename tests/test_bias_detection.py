"""Tests for S3 bias detection validation."""

import duckdb
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """In-memory DuckDB with migrations, test images, votes, and scores."""
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

    # Generate synthetic votes (small scale)
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    generate_synthetic_votes(
        c,
        seed=42,
        voter_count=20,
        ballot_count=10,
        pair_count=40,
        ranking_count=5,
    )

    # Insert visual cluster assignments for all images
    image_sks = [r[0] for r in c.execute("SELECT image_sk FROM dim_image WHERE vote_pool_flag = true").fetchall()]
    for idx, sk in enumerate(image_sks):
        cluster_id = idx % 5  # 5 clusters
        c.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_type, cluster_algorithm, cluster_id, cluster_label, cluster_run_id)
               VALUES (?, 'visual', 'kmeans', ?, ?, 'test-run')""",
            [sk, cluster_id, str(cluster_id)],
        )

    # Compute preference scores so mart_image_preference_score exists
    from artemis_calendar.models import compute_preference_scores

    compute_preference_scores(c)

    yield c
    c.close()


def test_detect_position_bias(conn):
    from artemis_calendar.validate.bias_detection import detect_position_bias

    result = detect_position_bias(conn)

    assert result["position_bias_coeff"] is not None
    assert result["position_bias_pvalue"] is not None
    assert isinstance(result["position_bias_detected"], bool)
    assert result["pairwise_left_win_rate"] is not None
    assert 0.0 <= result["pairwise_left_win_rate"] <= 1.0


def test_detect_cluster_bias(conn):
    from artemis_calendar.validate.bias_detection import detect_cluster_bias

    result = detect_cluster_bias(conn)

    assert result["cluster_bias_chi2"] is not None
    assert result["cluster_bias_pvalue"] is not None
    assert result["cluster_bias_chi2"] >= 0
    assert 0.0 <= result["cluster_bias_pvalue"] <= 1.0


def test_segment_voters(conn):
    from artemis_calendar.validate.bias_detection import segment_voters

    result = segment_voters(conn)

    assert result["voter_segment_count"] > 0
    assert result["voter_consensus_std"] is not None
    assert len(result["profile_stats"]) > 0

    # Should have at least neutral and one other profile
    profiles = set(result["profile_stats"].keys())
    assert "neutral" in profiles


def test_compare_scores_to_truth(conn):
    from artemis_calendar.validate.bias_detection import compare_scores_to_truth

    result = compare_scores_to_truth(conn)

    assert result["score_vs_truth_spearman"] is not None
    assert result["score_vs_truth_pvalue"] is not None
    # Spearman rho should be positive (scores should correlate with truth)
    assert result["score_vs_truth_spearman"] > 0


def test_reliability_under_bias(conn):
    from artemis_calendar.validate.bias_detection import reliability_under_bias

    result = reliability_under_bias(conn)

    assert result["alpha_all_voters"] is not None
    assert result["alpha_excluding_biased"] is not None
    assert result["alpha_delta"] is not None


def test_run_bias_detection_orchestrator(conn):
    from artemis_calendar.validate.bias_detection import run_bias_detection

    report = run_bias_detection(conn)

    assert "detection_run_id" in report
    assert report["detection_run_id"] is not None

    # Verify it was persisted
    rows = conn.execute("SELECT count(*) FROM mart_bias_detection").fetchone()[0]
    assert rows == 1

    # Verify all expected keys exist
    expected_keys = [
        "position_bias_coeff",
        "position_bias_pvalue",
        "position_bias_detected",
        "cluster_bias_chi2",
        "cluster_bias_pvalue",
        "score_vs_truth_spearman",
        "alpha_all_voters",
    ]
    for key in expected_keys:
        assert key in report, f"Missing key: {key}"


def test_run_bias_detection_idempotent(conn):
    from artemis_calendar.validate.bias_detection import run_bias_detection

    report1 = run_bias_detection(conn)
    report2 = run_bias_detection(conn)

    # Should have 2 rows (different run IDs)
    rows = conn.execute("SELECT count(*) FROM mart_bias_detection").fetchone()[0]
    assert rows == 2
    assert report1["detection_run_id"] != report2["detection_run_id"]
