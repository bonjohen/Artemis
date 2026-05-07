"""Tests for the statistical modeling / scoring module."""

import duckdb
import numpy as np
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """In-memory DuckDB with migrations + test vote data."""
    c = duckdb.connect(":memory:")
    apply_migrations(c, migrations_dir=MIGRATIONS_DIR)

    # Insert 20 test images
    for i in range(20):
        c.execute(
            """INSERT INTO dim_image (source_image_id, vote_pool_flag, timeline_flag, enabled_flag)
               VALUES (?, true, ?, ?)""",
            [f"ART002-E-{10000 + i}", i < 5, i < 10],
        )

    # Insert a category
    c.execute(
        """INSERT INTO dim_category (category_key, category_slug, category_label, image_count)
           VALUES ('test', 'test', 'Test', 20)"""
    )
    c.execute(
        """INSERT INTO stg_category
           (load_run_id, category_key, category_slug, category_label, image_count, showcase_guid)
           VALUES ('test', 'test', 'test', 'Test', 20, 'ART002-E-10000')"""
    )

    # Generate small synthetic vote set
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    generate_synthetic_votes(c, seed=42, voter_count=10, ballot_count=10, pair_count=50, ranking_count=5)

    yield c
    c.close()


class TestBatchScores:
    def test_returns_scores_for_shown_images(self, conn):
        from artemis_calendar.models.batch_scores import compute_batch_scores

        scores = compute_batch_scores(conn)
        assert len(scores) > 0
        for _img_sk, s in scores.items():
            assert s["shown_count"] > 0
            assert 0 <= s["selection_rate"] <= 1
            assert 0 <= s["wilson_lower"] <= 1
            assert 0 < s["posterior_mean"] < 1
            assert s["posterior_lower"] < s["posterior_upper"]

    def test_polarization_values(self, conn):
        from artemis_calendar.models.batch_scores import compute_polarization

        polar = compute_polarization(conn)
        assert len(polar) > 0
        for _img_sk, val in polar.items():
            assert val >= 0


class TestWilsonLower:
    def test_zero_shown(self):
        from artemis_calendar.models.batch_scores import _wilson_lower

        assert _wilson_lower(0, 0) == 0.0

    def test_all_selected(self):
        from artemis_calendar.models.batch_scores import _wilson_lower

        w = _wilson_lower(10, 10)
        assert 0.5 < w < 1.0

    def test_none_selected(self):
        from artemis_calendar.models.batch_scores import _wilson_lower

        w = _wilson_lower(0, 10)
        assert w == 0.0 or w < 0.1

    def test_monotonic(self):
        from artemis_calendar.models.batch_scores import _wilson_lower

        w1 = _wilson_lower(1, 10)
        w2 = _wilson_lower(5, 10)
        w3 = _wilson_lower(9, 10)
        assert w1 < w2 < w3


class TestEloScores:
    def test_returns_scores(self, conn):
        from artemis_calendar.models.pairwise_scores import compute_elo_scores

        scores = compute_elo_scores(conn)
        assert len(scores) > 0
        for _img_sk, s in scores.items():
            assert isinstance(s["elo_score"], float)
            assert s["pairwise_wins"] >= 0
            assert s["pairwise_losses"] >= 0
            assert s["pairwise_wins"] + s["pairwise_losses"] > 0

    def test_winners_rated_higher(self, conn):
        from artemis_calendar.models.pairwise_scores import compute_elo_scores

        scores = compute_elo_scores(conn)
        # Images with more wins than losses should tend to have higher Elo
        high_win = [s for s in scores.values() if s["pairwise_wins"] > s["pairwise_losses"]]
        high_loss = [s for s in scores.values() if s["pairwise_losses"] > s["pairwise_wins"]]
        if high_win and high_loss:
            avg_winner_elo = sum(s["elo_score"] for s in high_win) / len(high_win)
            avg_loser_elo = sum(s["elo_score"] for s in high_loss) / len(high_loss)
            assert avg_winner_elo > avg_loser_elo


class TestBordaScores:
    def test_returns_scores(self, conn):
        from artemis_calendar.models.category_scores import compute_borda_scores

        scores = compute_borda_scores(conn)
        assert len(scores) > 0
        for _img_sk, s in scores.items():
            assert s["borda_score"] > 0
            assert s["borda_count"] > 0
            assert s["borda_mean"] > 0


class TestComposite:
    def test_all_images_scored(self, conn):
        from artemis_calendar.models.batch_scores import compute_batch_scores, compute_polarization
        from artemis_calendar.models.category_scores import compute_borda_scores
        from artemis_calendar.models.composite import compute_composite_scores
        from artemis_calendar.models.pairwise_scores import compute_elo_scores

        all_sks = [
            int(r[0]) for r in conn.execute("SELECT image_sk FROM dim_image WHERE vote_pool_flag = true").fetchall()
        ]

        composite = compute_composite_scores(
            batch_scores=compute_batch_scores(conn),
            elo_scores=compute_elo_scores(conn),
            borda_scores=compute_borda_scores(conn),
            polarization=compute_polarization(conn),
            all_image_sks=all_sks,
        )

        assert len(composite) == len(all_sks)
        for _img_sk, s in composite.items():
            assert s["posterior_mean"] > 0
            assert s["posterior_lower"] < s["posterior_upper"]
            assert s["uncertainty_score"] > 0
            assert s["broad_appeal_score"] >= 0


class TestReliability:
    def test_krippendorff_perfect_agreement(self):
        from artemis_calendar.models.reliability import krippendorff_alpha_nominal

        # Perfect agreement: all raters agree
        matrix = np.array(
            [
                [1, 0, 1, 0],
                [1, 0, 1, 0],
                [1, 0, 1, 0],
            ],
            dtype=float,
        )
        alpha = krippendorff_alpha_nominal(matrix)
        assert alpha is not None
        assert alpha > 0.9

    def test_krippendorff_random(self):
        from artemis_calendar.models.reliability import krippendorff_alpha_nominal

        rng = np.random.RandomState(42)
        matrix = rng.randint(0, 2, size=(10, 20)).astype(float)
        alpha = krippendorff_alpha_nominal(matrix)
        assert alpha is not None
        # Random data should have low alpha
        assert alpha < 0.3

    def test_krippendorff_with_missing(self):
        from artemis_calendar.models.reliability import krippendorff_alpha_nominal

        matrix = np.array(
            [
                [1, np.nan, 1, 0],
                [1, 0, np.nan, 0],
                [np.nan, 0, 1, 0],
            ]
        )
        alpha = krippendorff_alpha_nominal(matrix)
        assert alpha is not None

    def test_compute_reliability_from_db(self, conn):
        from artemis_calendar.models.reliability import compute_reliability

        results = compute_reliability(conn)
        assert "batch_pick_5_of_50" in results
        batch = results["batch_pick_5_of_50"]
        assert batch["voter_count"] > 0
        assert batch["image_count"] > 0
        assert 0 < batch["rating_density"] <= 1
        assert batch["krippendorff_alpha"] is not None


class TestMarts:
    def test_full_pipeline(self, conn):
        from artemis_calendar.models import compute_preference_scores

        counts = compute_preference_scores(conn)
        assert counts["preference_scores"] == 20  # 20 test images
        assert counts["reliability_results"] >= 1

        # Verify mart_image_preference_score populated
        pref_count = conn.execute("SELECT count(*) FROM mart_image_preference_score").fetchone()[0]
        assert pref_count == 20

        # Verify reliability written
        irr_count = conn.execute("SELECT count(*) FROM mart_inter_rater_reliability").fetchone()[0]
        assert irr_count >= 1

    def test_idempotent(self, conn):
        from artemis_calendar.models import compute_preference_scores

        counts1 = compute_preference_scores(conn)
        counts2 = compute_preference_scores(conn)
        # Second run should produce same counts
        assert counts2["preference_scores"] == counts1["preference_scores"]
        # Each run gets its own run_id, so both exist; verify per-run count is correct
        run_id = counts2["score_run_id"]
        per_run = conn.execute(
            "SELECT count(*) FROM mart_image_preference_score WHERE score_run_id = ?",
            [run_id],
        ).fetchone()[0]
        assert per_run == 20
