"""Five calendar selection methods (A-E) for choosing 13 images."""

from __future__ import annotations

import numpy as np

from artemis_calendar.config.settings import (
    MMR_W_APPEAL,
    MMR_W_MONTH_FIT,
    MMR_W_POPULARITY,
    MMR_W_REDUNDANCY,
    MMR_W_UNCERTAINTY,
)
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.optimize.methods")


def method_a_top_popularity(
    image_sks: list[int],
    preference: dict[int, float],
) -> list[int]:
    """Method A: Top 13 by posterior_mean (naive baseline)."""
    ranked = sorted(image_sks, key=lambda sk: preference.get(sk, 0.0), reverse=True)
    selected = ranked[:13]
    logger.info("Method A: selected top 13 by popularity")
    return selected


def method_b_cluster_limited(
    image_sks: list[int],
    preference: dict[int, float],
    clusters: dict[int, int],
    max_per_cluster: int = 2,
) -> list[int]:
    """Method B: Top by popularity, max 2 per visual cluster."""
    ranked = sorted(image_sks, key=lambda sk: preference.get(sk, 0.0), reverse=True)
    selected = []
    cluster_counts: dict[int, int] = {}

    for sk in ranked:
        if len(selected) >= 13:
            break
        cid = clusters.get(sk, -1)
        if cluster_counts.get(cid, 0) < max_per_cluster:
            selected.append(sk)
            cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

    logger.info(f"Method B: selected {len(selected)} images with cluster limit {max_per_cluster}")
    return selected


def method_c_per_cluster(
    image_sks: list[int],
    preference: dict[int, float],
    clusters: dict[int, int],
) -> list[int]:
    """Method C: Best image from top 13 clusters by mean preference."""
    # Group images by cluster
    cluster_images: dict[int, list[int]] = {}
    for sk in image_sks:
        cid = clusters.get(sk, -1)
        if cid < 0:
            continue
        cluster_images.setdefault(cid, []).append(sk)

    # Rank clusters by mean preference
    cluster_means = {}
    for cid, sks in cluster_images.items():
        scores = [preference.get(sk, 0.0) for sk in sks]
        cluster_means[cid] = np.mean(scores) if scores else 0.0

    top_clusters = sorted(cluster_means, key=lambda c: cluster_means[c], reverse=True)[:13]

    # Best image from each top cluster
    selected = []
    for cid in top_clusters:
        sks = cluster_images[cid]
        best = max(sks, key=lambda sk: preference.get(sk, 0.0))
        selected.append(best)

    logger.info(f"Method C: selected best from top {len(selected)} clusters")
    return selected


def method_d_month_first(
    image_sks: list[int],
    preference: dict[int, float],
    month_fit: dict[int, np.ndarray],
    clusters: dict[int, int],
    max_per_cluster: int = 2,
) -> list[int]:
    """Method D: Best image for each month (greedy, cluster-constrained).

    For each month slot, pick the image with highest month_fit * preference
    that doesn't violate cluster limits.
    """
    selected = []
    used = set()
    cluster_counts: dict[int, int] = {}

    for month_idx in range(13):
        best_sk = None
        best_score = -1.0

        for sk in image_sks:
            if sk in used:
                continue
            cid = clusters.get(sk, -1)
            if cluster_counts.get(cid, 0) >= max_per_cluster:
                continue

            mf = month_fit.get(sk)
            if mf is None:
                continue
            score = mf[month_idx] * 0.6 + preference.get(sk, 0.0) * 0.4

            if score > best_score:
                best_score = score
                best_sk = sk

        if best_sk is not None:
            selected.append(best_sk)
            used.add(best_sk)
            cid = clusters.get(best_sk, -1)
            cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

    logger.info(f"Method D: selected {len(selected)} images month-first")
    return selected


def method_e_mmr_greedy(
    image_sks: list[int],
    preference: dict[int, float],
    broad_appeal: dict[int, float],
    month_fit: dict[int, np.ndarray],
    uncertainty: dict[int, float],
    embeddings: dict[int, np.ndarray],
    clusters: dict[int, int],
    max_per_cluster: int = 2,
    w_pop: float = MMR_W_POPULARITY,
    w_appeal: float = MMR_W_APPEAL,
    w_monthfit: float = MMR_W_MONTH_FIT,
    w_redundancy: float = MMR_W_REDUNDANCY,
    w_uncertainty: float = MMR_W_UNCERTAINTY,
) -> list[int]:
    """Method E: Multi-objective greedy selection via maximum marginal relevance.

    At each step, adds the image that maximizes:
        w_pop * preference_quantile
      + w_appeal * broad_appeal_quantile
      + w_monthfit * best_remaining_month_fit
      - w_redundancy * max_cosine_similarity_to_selected
      - w_uncertainty * uncertainty_quantile
    """
    # Quantile-rank preference and appeal
    pref_q = _quantile_rank(preference, image_sks)
    appeal_q = _quantile_rank(broad_appeal, image_sks)
    unc_q = _quantile_rank(uncertainty, image_sks)

    # L2-normalize embeddings for cosine similarity
    normed: dict[int, np.ndarray] = {}
    for sk in image_sks:
        emb = embeddings.get(sk)
        if emb is not None:
            norm = np.linalg.norm(emb)
            normed[sk] = emb / norm if norm > 0 else emb

    selected: list[int] = []
    used_months: set[int] = set()
    cluster_counts: dict[int, int] = {}
    remaining = set(image_sks)

    for _step in range(13):
        best_sk = None
        best_utility = -float("inf")

        for sk in remaining:
            # Cluster constraint
            cid = clusters.get(sk, -1)
            if cluster_counts.get(cid, 0) >= max_per_cluster:
                continue

            # Preference + appeal
            utility = w_pop * pref_q.get(sk, 0.5) + w_appeal * appeal_q.get(sk, 0.5)

            # Best available month fit
            mf = month_fit.get(sk)
            if mf is not None:
                available_fits = [mf[m] for m in range(13) if m not in used_months]
                if available_fits:
                    utility += w_monthfit * max(available_fits)

            # Redundancy: max cosine similarity to any selected image
            if selected and sk in normed:
                max_sim = 0.0
                for sel_sk in selected:
                    if sel_sk in normed:
                        sim = float(np.dot(normed[sk], normed[sel_sk]))
                        max_sim = max(max_sim, sim)
                utility -= w_redundancy * max_sim

            # Uncertainty penalty
            utility -= w_uncertainty * unc_q.get(sk, 0.5)

            if utility > best_utility:
                best_utility = utility
                best_sk = sk

        if best_sk is None:
            break

        selected.append(best_sk)
        remaining.discard(best_sk)
        cid = clusters.get(best_sk, -1)
        cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

        # Track which month this image best fits (for month-fit lookahead)
        mf = month_fit.get(best_sk)
        if mf is not None:
            available = [m for m in range(13) if m not in used_months]
            if available:
                best_month = max(available, key=lambda m: mf[m])
                used_months.add(best_month)

    logger.info(f"Method E: selected {len(selected)} images via MMR greedy")
    return selected


def _quantile_rank(values: dict[int, float], image_sks: list[int]) -> dict[int, float]:
    """Rank values to [0, 1] quantiles for the given image set."""
    vals = np.array([values.get(sk, 0.0) for sk in image_sks])
    ranks = np.argsort(np.argsort(vals)).astype(np.float64)
    n = len(vals)
    if n > 1:
        ranks /= n - 1
    return dict(zip(image_sks, ranks, strict=True))
