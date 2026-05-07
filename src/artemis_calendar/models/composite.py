"""Composite preference scoring: merge batch, Elo, and Borda into unified scores."""

from __future__ import annotations

import numpy as np

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.composite")

# Prior for images with no batch data at all
PRIOR_ALPHA = 2.0
PRIOR_BETA = 8.0

# Adjustment weights for secondary signals
ELO_WEIGHT = 0.15
BORDA_WEIGHT = 0.10


def compute_composite_scores(
    batch_scores: dict[int, dict],
    elo_scores: dict[int, dict],
    borda_scores: dict[int, dict],
    polarization: dict[int, float],
    all_image_sks: list[int],
) -> dict[int, dict]:
    """Merge all scoring components into a composite preference score.

    For each image:
    - Base: Beta posterior mean from batch data (or pure prior if no batch data)
    - Adjustment: Elo and Borda quantile ranks as multiplicative boosts
    - Uncertainty: credible interval width
    - Polarization: voter disagreement
    - Broad appeal: posterior mean penalized by polarization

    Returns dict keyed by image_sk with all mart_image_preference_score columns.
    """
    # Compute quantile ranks for Elo and Borda scores
    elo_quantiles = _quantile_ranks({k: v["elo_score"] for k, v in elo_scores.items()})
    borda_quantiles = _quantile_ranks({k: v["borda_score"] for k, v in borda_scores.items()})
    polar_quantiles = _quantile_ranks(polarization)

    from scipy.stats import beta as beta_dist

    results: dict[int, dict] = {}
    for image_sk in all_image_sks:
        batch = batch_scores.get(image_sk)
        elo = elo_scores.get(image_sk)
        borda = borda_scores.get(image_sk)

        # Base posterior from batch data
        if batch:
            post_mean = batch["posterior_mean"]
            post_lower = batch["posterior_lower"]
            post_upper = batch["posterior_upper"]
            shown = batch["shown_count"]
            selected = batch["selected_count"]
            sel_rate = batch["selection_rate"]
            wilson = batch["wilson_lower"]
        else:
            # Pure prior for images never shown in batch voting
            post_mean = PRIOR_ALPHA / (PRIOR_ALPHA + PRIOR_BETA)
            post_lower = float(beta_dist.ppf(0.025, PRIOR_ALPHA, PRIOR_BETA))
            post_upper = float(beta_dist.ppf(0.975, PRIOR_ALPHA, PRIOR_BETA))
            shown = 0
            selected = 0
            sel_rate = None
            wilson = None

        # Multiplicative adjustment from secondary signals
        elo_adj = ELO_WEIGHT * elo_quantiles.get(image_sk, 0.0) if elo else 0.0
        borda_adj = BORDA_WEIGHT * borda_quantiles.get(image_sk, 0.0) if borda else 0.0
        adjusted_mean = post_mean * (1.0 + elo_adj + borda_adj)

        uncertainty = post_upper - post_lower
        polar_val = polarization.get(image_sk, 0.0)
        polar_q = polar_quantiles.get(image_sk, 0.0)
        broad_appeal = adjusted_mean * (1.0 - polar_q)

        results[image_sk] = {
            "shown_count": shown,
            "selected_count": selected,
            "selection_rate": sel_rate,
            "wilson_lower": wilson,
            "elo_score": elo["elo_score"] if elo else None,
            "pairwise_wins": elo["pairwise_wins"] if elo else None,
            "pairwise_losses": elo["pairwise_losses"] if elo else None,
            "btl_score": None,  # TODO: BTL when pairwise data reaches ~20K+
            "borda_score": borda["borda_score"] if borda else None,
            "posterior_mean": adjusted_mean,
            "posterior_lower": post_lower,
            "posterior_upper": post_upper,
            "uncertainty_score": uncertainty,
            "polarization_score": polar_val,
            "broad_appeal_score": broad_appeal,
        }

    logger.info(
        f"Computed composite scores for {len(results)} images "
        f"(batch: {len(batch_scores)}, elo: {len(elo_scores)}, borda: {len(borda_scores)})"
    )
    return results


def _quantile_ranks(values: dict[int, float]) -> dict[int, float]:
    """Convert raw values to quantile ranks in [0, 1]."""
    if not values:
        return {}
    keys = list(values.keys())
    vals = np.array([values[k] for k in keys])
    # Rank from 0 to 1
    order = vals.argsort().argsort()
    n = len(vals)
    quantiles = order / max(n - 1, 1)
    return dict(zip(keys, quantiles.tolist(), strict=True))
