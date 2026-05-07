"""Cover suitability scoring for calendar cover image selection."""

from __future__ import annotations

import numpy as np

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.optimize.cover_fit")


def _quantile_rank(values: dict[int, float]) -> dict[int, float]:
    """Rank values to [0, 1] quantiles."""
    if not values:
        return {}
    sks = list(values.keys())
    vals = np.array([values[sk] for sk in sks])
    ranks = np.argsort(np.argsort(vals)).astype(np.float64)
    n = len(vals)
    if n > 1:
        ranks /= n - 1
    return dict(zip(sks, ranks, strict=True))


def compute_cover_fit_scores(
    image_sks: list[int],
    broad_appeal: dict[int, float],
    contrast: dict[int, float],
    saturation: dict[int, float],
) -> dict[int, float]:
    """Compute cover suitability score for each image.

    Cover score = 0.50 * broad_appeal_quantile
               + 0.30 * visual_impact_quantile
               + 0.10 * contrast_quantile
               + 0.10 * saturation_quantile

    Returns dict mapping image_sk to cover_fit score in [0, 1].
    """
    # Compute visual impact = contrast * saturation
    visual_impact = {sk: contrast.get(sk, 0.5) * saturation.get(sk, 0.5) for sk in image_sks}

    # Quantile-rank each component
    appeal_q = _quantile_rank({sk: broad_appeal.get(sk, 0.0) for sk in image_sks})
    impact_q = _quantile_rank(visual_impact)
    contrast_q = _quantile_rank({sk: contrast.get(sk, 0.5) for sk in image_sks})
    sat_q = _quantile_rank({sk: saturation.get(sk, 0.5) for sk in image_sks})

    result = {}
    for sk in image_sks:
        score = (
            0.50 * appeal_q.get(sk, 0.5)
            + 0.30 * impact_q.get(sk, 0.5)
            + 0.10 * contrast_q.get(sk, 0.5)
            + 0.10 * sat_q.get(sk, 0.5)
        )
        result[sk] = score

    logger.info(f"Computed cover-fit scores for {len(result)} images")
    return result
