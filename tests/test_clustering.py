"""Tests for clustering module."""

import numpy as np
import pytest

from artemis_calendar.cluster.clustering import _run_hdbscan, _run_kmeans


class TestKMeans:
    def test_all_assigned(self):
        vectors = np.random.randn(50, 10).astype(np.float32)
        labels, distances = _run_kmeans(vectors, n_clusters=5, seed=42)
        assert len(labels) == 50
        assert len(distances) == 50
        assert set(labels) <= set(range(5))

    def test_reproducible(self):
        vectors = np.random.randn(50, 10).astype(np.float32)
        labels1, dist1 = _run_kmeans(vectors, n_clusters=5, seed=42)
        labels2, dist2 = _run_kmeans(vectors, n_clusters=5, seed=42)
        np.testing.assert_array_equal(labels1, labels2)
        np.testing.assert_array_almost_equal(dist1, dist2)

    def test_different_seeds(self):
        vectors = np.random.randn(100, 10).astype(np.float32)
        labels1, _ = _run_kmeans(vectors, n_clusters=5, seed=42)
        labels2, _ = _run_kmeans(vectors, n_clusters=5, seed=99)
        # Different seeds should (very likely) produce different labels
        # Not guaranteed but extremely likely with 100 points
        assert not np.array_equal(labels1, labels2)

    def test_n_clusters_capped(self):
        vectors = np.random.randn(3, 10).astype(np.float32)
        labels, distances = _run_kmeans(vectors, n_clusters=10, seed=42)
        assert len(labels) == 3
        assert max(labels) < 3

    def test_distances_non_negative(self):
        vectors = np.random.randn(20, 5).astype(np.float32)
        _, distances = _run_kmeans(vectors, n_clusters=3, seed=42)
        assert all(d >= 0 for d in distances)


class TestHDBSCAN:
    def test_basic(self):
        # Create well-separated clusters
        rng = np.random.RandomState(42)
        c1 = rng.randn(30, 5) + np.array([5, 0, 0, 0, 0])
        c2 = rng.randn(30, 5) + np.array([0, 5, 0, 0, 0])
        c3 = rng.randn(30, 5) + np.array([0, 0, 5, 0, 0])
        vectors = np.vstack([c1, c2, c3]).astype(np.float32)

        labels, distances = _run_hdbscan(vectors, min_cluster_size=5)
        assert len(labels) == 90
        assert len(distances) == 90
        # Should find at least 2 clusters (HDBSCAN might merge some)
        real_labels = set(labels) - {-1}
        assert len(real_labels) >= 2


class TestClusteringIntegration:
    @pytest.fixture
    def conn_with_embeddings(self):
        """Create an in-memory DB with migrations and fake embeddings."""
        import duckdb

        from artemis_calendar.config.database import apply_migrations
        from artemis_calendar.config.settings import MIGRATIONS_DIR

        c = duckdb.connect(":memory:")
        apply_migrations(c, migrations_dir=MIGRATIONS_DIR)

        # Insert test images
        for i in range(20):
            c.execute(
                """INSERT INTO dim_image (
                    source_image_id, vote_pool_flag, timeline_flag,
                    enabled_flag, thumb_downloaded, title, description
                ) VALUES (?, true, true, true, true, ?, ?)""",
                [f"TEST-{i}", f"Image {i}", f"Description of image {i} in space"],
            )

        # Insert fake visual features
        image_sks = [r[0] for r in c.execute("SELECT image_sk FROM dim_image ORDER BY image_sk").fetchall()]
        rng = np.random.RandomState(42)
        for sk in image_sks:
            c.execute(
                """INSERT INTO feature_image_visual (
                    image_sk, feature_run_id, orientation,
                    aspect_ratio, brightness_score, contrast_score, saturation_score
                ) VALUES (?, 'test', 'landscape', ?, ?, ?, ?)""",
                [sk, 1.5, float(rng.random()), float(rng.random()), float(rng.random())],
            )

        # Insert fake image embeddings (512-dim)
        for sk in image_sks:
            vec = rng.randn(512).astype(np.float32).tolist()
            c.execute(
                """INSERT INTO feature_image_embedding (
                    image_sk, embedding_model, embedding_model_version,
                    embedding_vector, embedding_dimension
                ) VALUES (?, 'CLIP', 'openai/clip-vit-base-patch32', ?::FLOAT[], 512)""",
                [sk, vec],
            )

        # Insert fake text embeddings (384-dim)
        for sk in image_sks:
            vec = rng.randn(384).astype(np.float32).tolist()
            c.execute(
                """INSERT INTO feature_description_embedding (
                    image_sk, embedding_model, embedding_model_version,
                    text_source, embedding_vector, embedding_dimension
                ) VALUES (
                    ?, 'sentence-transformers', 'all-MiniLM-L6-v2',
                    'metadata_combined', ?::FLOAT[], 384
                )""",
                [sk, vec],
            )

        # Insert fake text features
        for sk in image_sks:
            c.execute(
                """INSERT INTO feature_description_text (
                    image_sk, feature_run_id, sentiment_score, subjectivity_score
                ) VALUES (?, 'test', ?, ?)""",
                [sk, float(rng.uniform(-1, 1)), float(rng.random())],
            )

        # Insert run_manifest entry (needed by create_run_record)
        yield c
        c.close()

    def test_kmeans_all_types(self, conn_with_embeddings):
        from artemis_calendar.cluster.clustering import run_clustering

        results = run_clustering(
            conn_with_embeddings,
            algorithm="kmeans",
            cluster_type="all",
            n_clusters=3,
            seed=42,
        )
        assert results["visual"] == 20
        assert results["text"] == 20
        assert results["multimodal"] == 20

        # Verify all cluster assignments are in the table
        count = conn_with_embeddings.execute("SELECT count(*) FROM feature_image_cluster").fetchone()[0]
        assert count == 60  # 20 images * 3 types

    def test_marts_populated(self, conn_with_embeddings):
        from artemis_calendar.cluster.clustering import run_clustering
        from artemis_calendar.cluster.marts import build_cluster_summary, build_cluster_top_images

        run_clustering(
            conn_with_embeddings,
            algorithm="kmeans",
            cluster_type="visual",
            n_clusters=3,
            seed=42,
        )

        run_id = conn_with_embeddings.execute(
            "SELECT DISTINCT cluster_run_id FROM feature_image_cluster LIMIT 1"
        ).fetchone()[0]

        summary_count = build_cluster_summary(conn_with_embeddings, run_id)
        assert summary_count == 3  # 3 clusters

        top_count = build_cluster_top_images(conn_with_embeddings, run_id, top_n=3)
        assert top_count > 0
        assert top_count <= 9  # at most 3 per cluster

        # Verify top_image_sk is populated in summary
        top_sks = conn_with_embeddings.execute(
            "SELECT top_image_sk FROM mart_image_cluster_summary WHERE cluster_run_id = ?",
            [run_id],
        ).fetchall()
        assert all(sk[0] is not None for sk in top_sks)

    def test_reproducible_clustering(self, conn_with_embeddings):
        from artemis_calendar.cluster.clustering import run_clustering

        run_clustering(
            conn_with_embeddings,
            algorithm="kmeans",
            cluster_type="visual",
            n_clusters=3,
            seed=42,
        )

        # Get first run's assignments
        assignments1 = conn_with_embeddings.execute(
            "SELECT image_sk, cluster_id FROM feature_image_cluster WHERE cluster_type = 'visual' ORDER BY image_sk"
        ).fetchall()

        # Clear and re-run
        conn_with_embeddings.execute("DELETE FROM feature_image_cluster")

        run_clustering(
            conn_with_embeddings,
            algorithm="kmeans",
            cluster_type="visual",
            n_clusters=3,
            seed=42,
        )

        assignments2 = conn_with_embeddings.execute(
            "SELECT image_sk, cluster_id FROM feature_image_cluster WHERE cluster_type = 'visual' ORDER BY image_sk"
        ).fetchall()

        assert assignments1 == assignments2
