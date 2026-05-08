"""Calendar-level scoring: evaluate a complete 13-image candidate."""

from __future__ import annotations

import numpy as np

from artemis_calendar.config.settings import (
    OBJECTIVE_W_COVER_FIT,
    OBJECTIVE_W_DIVERSITY,
    OBJECTIVE_W_MONTH_FIT,
    OBJECTIVE_W_POPULARITY,
    OBJECTIVE_W_REDUNDANCY,
    OBJECTIVE_W_UNCERTAINTY,
)
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.optimize.scoring")


def score_calendar(
    selected_sks: list[int],
    assignments: list[tuple[int, int, str]],
    preference: dict[int, float],
    month_fit: dict[int, np.ndarray],
    cover_fit: dict[int, float],
    uncertainty: dict[int, float],
    clusters: dict[int, int],
    embeddings: dict[int, np.ndarray] | None = None,
) -> dict:
    """Score a complete calendar candidate.

    Returns dict with component scores and total objective_score.
    """
    n = len(selected_sks)

    # Popularity: sum of posterior_mean
    popularity = sum(preference.get(sk, 0.0) for sk in selected_sks)

    # Diversity: fraction of distinct visual clusters
    cluster_ids = {clusters.get(sk, -sk) for sk in selected_sks}
    diversity = len(cluster_ids) / max(n, 1)

    # Month fit: sum of assigned month-fit scores
    total_month_fit = 0.0
    for sk, seq, _label in assignments:
        mf = month_fit.get(sk)
        if mf is not None and 0 < seq <= 13:
            total_month_fit += mf[seq - 1]

    # Cover fit: best cover score among selected
    cover_scores = {sk: cover_fit.get(sk, 0.0) for sk in selected_sks}
    cover_sk = max(cover_scores, key=lambda sk: cover_scores[sk]) if cover_scores else selected_sks[0]
    cover_score = cover_scores.get(cover_sk, 0.0)

    # Redundancy: max pairwise CLIP cosine similarity
    max_redundancy = 0.0
    if embeddings:
        normed = {}
        for sk in selected_sks:
            emb = embeddings.get(sk)
            if emb is not None:
                norm = np.linalg.norm(emb)
                normed[sk] = emb / norm if norm > 0 else emb

        for i, sk_i in enumerate(selected_sks):
            for sk_j in selected_sks[i + 1 :]:
                if sk_i in normed and sk_j in normed:
                    sim = float(np.dot(normed[sk_i], normed[sk_j]))
                    max_redundancy = max(max_redundancy, sim)

    # Uncertainty: sum of uncertainty scores
    total_uncertainty = sum(uncertainty.get(sk, 0.0) for sk in selected_sks)

    # Objective: weighted combination
    objective = (
        popularity * OBJECTIVE_W_POPULARITY
        + diversity * OBJECTIVE_W_DIVERSITY
        + total_month_fit * OBJECTIVE_W_MONTH_FIT
        + cover_score * OBJECTIVE_W_COVER_FIT
        - max_redundancy * OBJECTIVE_W_REDUNDANCY
        - total_uncertainty * OBJECTIVE_W_UNCERTAINTY
    )

    return {
        "cover_image_sk": cover_sk,
        "objective_score": round(objective, 4),
        "popularity_score": round(popularity, 4),
        "diversity_score": round(diversity, 4),
        "month_fit_score": round(total_month_fit, 4),
        "cover_fit_score": round(cover_score, 4),
        "redundancy_penalty": round(max_redundancy, 4),
        "uncertainty_penalty": round(total_uncertainty, 4),
    }
