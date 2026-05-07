"""Tests for the calendar optimization module."""

import duckdb
import numpy as np
import pytest

from artemis_calendar.config.database import apply_migrations
from artemis_calendar.config.settings import MIGRATIONS_DIR


@pytest.fixture
def conn():
    """In-memory DuckDB with migrations + test data for optimization."""
    c = duckdb.connect(":memory:")
    apply_migrations(c, migrations_dir=MIGRATIONS_DIR)

    # Insert 30 test images
    for i in range(30):
        c.execute(
            """INSERT INTO dim_image (source_image_id, vote_pool_flag, timeline_flag, enabled_flag)
               VALUES (?, true, ?, ?)""",
            [f"ART002-E-{10000 + i}", i < 5, i < 10],
        )

    # Get image SKs
    sks = [r[0] for r in c.execute("SELECT image_sk FROM dim_image").fetchall()]

    # Insert preference scores
    rng = np.random.default_rng(42)
    for sk in sks:
        pm = float(rng.uniform(0.15, 0.40))
        ba = float(pm * rng.uniform(0.6, 1.0))
        unc = float(rng.uniform(0.05, 0.30))
        c.execute(
            """INSERT INTO mart_image_preference_score
               (score_run_id, image_sk, posterior_mean, broad_appeal_score, uncertainty_score,
                shown_count, selected_count, selection_rate)
               VALUES ('test_run', ?, ?, ?, ?, 50, 5, 0.1)""",
            [sk, pm, ba, unc],
        )

    # Insert visual features
    for i, sk in enumerate(sks):
        br = float(rng.uniform(0.2, 0.8))
        ct = float(rng.uniform(0.2, 0.8))
        sat = float(rng.uniform(0.1, 0.6))
        r_val, g_val, b_val = rng.integers(0, 255), rng.integers(0, 255), rng.integers(0, 255)
        colors = f'[{{"r": {r_val}, "g": {g_val}, "b": {b_val}, "proportion": 0.5}}]'
        c.execute(
            """INSERT INTO feature_image_visual
               (image_sk, feature_run_id, brightness_score, contrast_score, saturation_score,
                dominant_color_json, has_earth_flag, has_moon_flag, has_crew_flag, has_spacecraft_flag,
                orientation, aspect_ratio)
               VALUES (?, 'test_run', ?, ?, ?, ?, ?, ?, ?, ?, 'landscape', 1.5)""",
            [sk, br, ct, sat, colors, i % 5 == 0, i % 7 == 0, i % 10 == 0, i % 8 == 0],
        )

    # Insert CLIP embeddings (random 512-dim)
    for sk in sks:
        vec = rng.normal(size=512).astype(np.float32).tolist()
        c.execute(
            """INSERT INTO feature_image_embedding
               (image_sk, embedding_model, embedding_model_version, embedding_vector, embedding_dimension)
               VALUES (?, 'CLIP', 'test', ?, 512)""",
            [sk, vec],
        )

    # Insert cluster assignments (3 clusters of 10)
    for i, sk in enumerate(sks):
        cid = i % 10  # 10 clusters
        c.execute(
            """INSERT INTO feature_image_cluster
               (image_sk, cluster_run_id, cluster_type, cluster_algorithm, cluster_id, distance_to_centroid)
               VALUES (?, 'test_run', 'visual', 'kmeans', ?, ?)""",
            [sk, cid, float(rng.uniform(0.1, 0.5))],
        )

    yield c
    c.close()


class TestMonthFit:
    def test_scores_shape(self):
        from artemis_calendar.optimize.month_fit import compute_month_fit_scores

        sks = [1, 2, 3]
        brightness = {1: 0.5, 2: 0.3, 3: 0.7}
        contrast = {1: 0.5, 2: 0.6, 3: 0.4}
        saturation = {1: 0.3, 2: 0.5, 3: 0.2}
        colors = {1: '[{"r": 200, "g": 100, "b": 50, "proportion": 0.5}]', 2: None, 3: None}
        flags = {1: {"earth": True, "moon": False, "crew": False, "spacecraft": False}, 2: {}, 3: {}}

        result = compute_month_fit_scores(sks, brightness, contrast, saturation, colors, flags)
        assert len(result) == 3
        for sk in sks:
            assert result[sk].shape == (13,)
            assert all(0 <= v <= 1 for v in result[sk])

    def test_warm_image_prefers_summer(self):
        from artemis_calendar.optimize.month_fit import compute_month_fit_scores

        # Warm, bright image should prefer summer months (seq 7=Jun, 8=Jul)
        sks = [1]
        result = compute_month_fit_scores(
            sks,
            brightness={1: 0.75},
            contrast={1: 0.3},
            saturation={1: 0.5},
            dominant_colors={1: '[{"r": 255, "g": 100, "b": 50, "proportion": 0.5}]'},
            content_flags={1: {}},
        )
        scores = result[1]
        summer_avg = np.mean([scores[6], scores[7]])  # Jun, Jul
        winter_avg = np.mean([scores[0], scores[11], scores[12]])  # Dec, Nov, Dec
        assert summer_avg > winter_avg


class TestCoverFit:
    def test_scores_range(self):
        from artemis_calendar.optimize.cover_fit import compute_cover_fit_scores

        sks = [1, 2, 3, 4, 5]
        appeal = {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.2, 5: 0.1}
        contrast = {1: 0.7, 2: 0.5, 3: 0.6, 4: 0.3, 5: 0.4}
        sat = {1: 0.6, 2: 0.4, 3: 0.5, 4: 0.2, 5: 0.3}

        result = compute_cover_fit_scores(sks, appeal, contrast, sat)
        assert len(result) == 5
        for sk in sks:
            assert 0 <= result[sk] <= 1
        # Highest appeal + impact should rank highest
        assert result[1] > result[5]


def _load_pref(conn):
    """Helper: load preference scores from test DB."""
    rows = conn.execute("SELECT image_sk, posterior_mean FROM mart_image_preference_score").fetchall()
    return {r[0]: r[1] for r in rows}


def _load_clusters(conn):
    """Helper: load visual cluster assignments from test DB."""
    rows = conn.execute("SELECT image_sk, cluster_id FROM feature_image_cluster WHERE cluster_type='visual'").fetchall()
    return {r[0]: r[1] for r in rows}


class TestMethods:
    def test_method_a_returns_13(self, conn):
        from artemis_calendar.optimize.methods import method_a_top_popularity

        pref = _load_pref(conn)
        sks = list(pref.keys())
        selected = method_a_top_popularity(sks, pref)
        assert len(selected) == 13
        assert len(set(selected)) == 13

    def test_method_b_cluster_constraint(self, conn):
        from artemis_calendar.optimize.methods import method_b_cluster_limited

        pref = _load_pref(conn)
        clusters = _load_clusters(conn)
        sks = list(pref.keys())
        selected = method_b_cluster_limited(sks, pref, clusters, max_per_cluster=2)
        assert len(selected) == 13

        # Check no cluster has more than 2
        from collections import Counter

        cluster_counts = Counter(clusters[sk] for sk in selected)
        assert max(cluster_counts.values()) <= 2

    def test_method_c_returns_13(self, conn):
        from artemis_calendar.optimize.methods import method_c_per_cluster

        pref = _load_pref(conn)
        clusters = _load_clusters(conn)
        sks = list(pref.keys())
        selected = method_c_per_cluster(sks, pref, clusters)
        # With 10 clusters for 30 images, we get 10
        assert len(selected) == min(13, len(set(clusters.values())))
        assert len(set(selected)) == len(selected)

    def test_method_e_returns_13(self, conn):
        from artemis_calendar.optimize.methods import method_e_mmr_greedy

        pref = _load_pref(conn)
        clusters = _load_clusters(conn)
        sks = list(pref.keys())

        appeal_rows = conn.execute("SELECT image_sk, broad_appeal_score FROM mart_image_preference_score").fetchall()
        appeal = {r[0]: r[1] for r in appeal_rows}

        unc_rows = conn.execute("SELECT image_sk, uncertainty_score FROM mart_image_preference_score").fetchall()
        unc = {r[0]: r[1] for r in unc_rows}

        emb_rows = conn.execute("SELECT image_sk, embedding_vector FROM feature_image_embedding").fetchall()
        embeddings = {int(r[0]): np.array(r[1], dtype=np.float32) for r in emb_rows}

        from artemis_calendar.optimize.month_fit import compute_month_fit_scores, load_visual_data

        vis_sks, brightness, contrast, saturation, colors, flags = load_visual_data(conn)
        month_fit = compute_month_fit_scores(vis_sks, brightness, contrast, saturation, colors, flags)

        selected = method_e_mmr_greedy(sks, pref, appeal, month_fit, unc, embeddings, clusters)
        assert len(selected) == 13
        assert len(set(selected)) == 13


class TestAssignment:
    def test_assigns_all_months(self):
        from artemis_calendar.optimize.assignment import assign_months

        sks = list(range(1, 14))
        month_fit = {sk: np.random.default_rng(sk).uniform(0, 1, size=13) for sk in sks}

        assignments = assign_months(sks, month_fit)
        assert len(assignments) == 13

        # Each sequence appears once
        sequences = [a[1] for a in assignments]
        assert sorted(sequences) == list(range(1, 14))

        # Each image appears once
        assigned_sks = [a[0] for a in assignments]
        assert len(set(assigned_sks)) == 13


class TestScoring:
    def test_score_components(self):
        from artemis_calendar.optimize.scoring import score_calendar

        sks = list(range(1, 14))
        assignments = [(sk, seq, f"Month {seq}") for sk, seq in zip(sks, range(1, 14), strict=True)]
        preference = {sk: 0.2 + sk * 0.01 for sk in sks}
        month_fit = {sk: np.full(13, 0.5) for sk in sks}
        cover_fit = {sk: 0.5 + sk * 0.01 for sk in sks}
        uncertainty = {sk: 0.1 for sk in sks}
        clusters = {sk: sk % 5 for sk in sks}

        result = score_calendar(sks, assignments, preference, month_fit, cover_fit, uncertainty, clusters)
        assert "objective_score" in result
        assert "popularity_score" in result
        assert "diversity_score" in result
        assert "cover_image_sk" in result
        assert result["diversity_score"] > 0


class TestIntegration:
    def test_full_optimization(self, conn):
        from artemis_calendar.optimize import run_calendar_optimization

        result = run_calendar_optimization(conn, seed=42)
        assert result["candidates"] == 5
        assert result["month_image_rows"] > 0

        # Verify candidates in DB
        count = conn.execute("SELECT count(*) FROM mart_calendar_candidate").fetchone()[0]
        assert count == 5

        # Verify month assignments
        month_count = conn.execute("SELECT count(*) FROM mart_calendar_candidate_month_image").fetchone()[0]
        assert month_count > 0

        # Each candidate should have unique images
        for name in ["method_a", "method_b", "method_e"]:
            images = conn.execute(
                "SELECT image_sk FROM mart_calendar_candidate_month_image WHERE candidate_name = ?", [name]
            ).fetchall()
            image_sks = [r[0] for r in images]
            assert len(image_sks) == len(set(image_sks)), f"{name} has duplicate images"
