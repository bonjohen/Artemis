"""Clustering of images using visual, text, and multimodal embeddings."""

from __future__ import annotations

import duckdb
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.cluster")

# Multimodal concatenation weights
WEIGHT_VISUAL = 0.60
WEIGHT_TEXT = 0.30
WEIGHT_METADATA = 0.10


def _load_embeddings(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    model_version: str | None = None,
) -> tuple[list[int], np.ndarray]:
    """Load embeddings from a feature table. Returns (image_sks, embedding_matrix)."""
    query = f"SELECT image_sk, embedding_vector FROM {table}"
    params = []
    if model_version:
        query += " WHERE embedding_model_version = ?"
        params.append(model_version)
    query += " ORDER BY image_sk"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        return [], np.empty((0, 0))

    image_sks = [r[0] for r in rows]
    vectors = np.array([r[1] for r in rows], dtype=np.float32)
    return image_sks, vectors


def _load_metadata_features(
    conn: duckdb.DuckDBPyConnection,
    image_sks: list[int],
) -> np.ndarray:
    """Load visual metadata features as a numeric matrix for multimodal clustering.

    Features: aspect_ratio, brightness_score, contrast_score, saturation_score.
    """
    if not image_sks:
        return np.empty((0, 4))

    placeholders = ",".join("?" * len(image_sks))
    rows = conn.execute(
        f"""
        SELECT image_sk, aspect_ratio, brightness_score, contrast_score, saturation_score
        FROM feature_image_visual
        WHERE image_sk IN ({placeholders})
        ORDER BY image_sk
        """,
        image_sks,
    ).fetchall()

    # Build a lookup for the metadata
    meta_map = {r[0]: r[1:] for r in rows}
    result = []
    for sk in image_sks:
        if sk in meta_map:
            result.append(list(meta_map[sk]))
        else:
            result.append([0.0, 0.0, 0.0, 0.0])

    return np.array(result, dtype=np.float32)


def _run_kmeans(vectors: np.ndarray, n_clusters: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Run k-means and return (labels, distances_to_centroid)."""
    n_clusters = min(n_clusters, len(vectors))
    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    km.fit(vectors)
    labels = km.labels_

    # Compute distance to assigned centroid
    distances = np.linalg.norm(vectors - km.cluster_centers_[labels], axis=1)
    return labels, distances


def _run_hdbscan(vectors: np.ndarray, min_cluster_size: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Run HDBSCAN and return (labels, distances_to_centroid).

    Noise points get label -1. Distance for noise = NaN.
    """
    import hdbscan

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    clusterer.fit(vectors)
    labels = clusterer.labels_

    # Compute distances to cluster centroids
    distances = np.full(len(vectors), np.nan)
    unique_labels = set(labels)
    unique_labels.discard(-1)
    for label in unique_labels:
        mask = labels == label
        centroid = vectors[mask].mean(axis=0)
        distances[mask] = np.linalg.norm(vectors[mask] - centroid, axis=1)

    return labels, distances


def _write_cluster_results(
    conn: duckdb.DuckDBPyConnection,
    *,
    image_sks: list[int],
    labels: np.ndarray,
    distances: np.ndarray,
    cluster_run_id: str,
    cluster_type: str,
    cluster_algorithm: str,
) -> int:
    """Insert cluster assignments into feature_image_cluster. Returns count."""
    count = 0
    for image_sk, label, dist in zip(image_sks, labels, distances, strict=True):
        conn.execute(
            """
            INSERT INTO feature_image_cluster (
                image_sk, cluster_run_id, cluster_type, cluster_algorithm,
                cluster_id, distance_to_centroid
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                image_sk,
                cluster_run_id,
                cluster_type,
                cluster_algorithm,
                int(label),
                float(dist) if not np.isnan(dist) else None,
            ],
        )
        count += 1
    return count


def run_clustering(
    conn: duckdb.DuckDBPyConnection,
    *,
    algorithm: str = "kmeans",
    cluster_type: str = "all",
    n_clusters: int = 25,
    seed: int = 42,
) -> dict[str, int]:
    """Run clustering on embeddings.

    cluster_type: 'visual', 'text', 'multimodal', or 'all'
    algorithm: 'kmeans' or 'hdbscan'
    Returns dict of cluster_type -> count of images clustered.
    """
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="run_clustering",
        dataset_name="feature_image_cluster",
        source_name="embeddings",
    )

    types = [cluster_type] if cluster_type != "all" else ["visual", "text", "multimodal"]
    results = {}

    for ctype in types:
        if ctype == "visual":
            image_sks, vectors = _load_embeddings(conn, "feature_image_embedding", "openai/clip-vit-base-patch32")
        elif ctype == "text":
            image_sks, vectors = _load_embeddings(conn, "feature_description_embedding", "all-MiniLM-L6-v2")
        elif ctype == "multimodal":
            vis_sks, vis_vectors = _load_embeddings(conn, "feature_image_embedding", "openai/clip-vit-base-patch32")
            txt_sks, txt_vectors = _load_embeddings(conn, "feature_description_embedding", "all-MiniLM-L6-v2")

            # Find common image_sks
            common_sks = sorted(set(vis_sks) & set(txt_sks))
            if not common_sks:
                logger.warning("No common images for multimodal clustering")
                results[ctype] = 0
                continue

            vis_map = dict(zip(vis_sks, vis_vectors, strict=True))
            txt_map = dict(zip(txt_sks, txt_vectors, strict=True))

            vis_arr = normalize(np.array([vis_map[sk] for sk in common_sks], dtype=np.float32))
            txt_arr = normalize(np.array([txt_map[sk] for sk in common_sks], dtype=np.float32))
            meta_arr = normalize(_load_metadata_features(conn, common_sks))

            # Handle zero-norm rows in metadata (all zeros → normalize produces nan)
            meta_arr = np.nan_to_num(meta_arr, nan=0.0)

            vectors = np.hstack([
                vis_arr * WEIGHT_VISUAL,
                txt_arr * WEIGHT_TEXT,
                meta_arr * WEIGHT_METADATA,
            ])
            image_sks = common_sks
        else:
            logger.warning(f"Unknown cluster type: {ctype}")
            continue

        if len(image_sks) == 0:
            logger.warning(f"No embeddings found for {ctype} clustering")
            results[ctype] = 0
            continue

        logger.info(f"Clustering {len(image_sks)} images ({ctype}, {algorithm})")

        if algorithm == "kmeans":
            labels, distances = _run_kmeans(vectors, n_clusters, seed)
        elif algorithm == "hdbscan":
            labels, distances = _run_hdbscan(vectors)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        count = _write_cluster_results(
            conn,
            image_sks=image_sks,
            labels=labels,
            distances=distances,
            cluster_run_id=run_id,
            cluster_type=ctype,
            cluster_algorithm=algorithm,
        )
        results[ctype] = count
        logger.info(f"{ctype} clustering: {count} assignments, {len(set(labels) - {-1})} clusters")

    total = sum(results.values())
    update_run_status(conn, run_id, row_count_raw=total, row_count_loaded=total, load_status="complete")
    return results
