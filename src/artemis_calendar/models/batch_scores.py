"""Batch voting scores: selection rate, Wilson lower bound, Beta-Binomial posterior."""

from __future__ import annotations

import math

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.batch")


def compute_batch_scores(conn: duckdb.DuckDBPyConnection) -> dict[int, dict]:
    """Compute batch-based preference scores for all images.

    Returns dict keyed by image_sk with keys:
        shown_count, selected_count, selection_rate, wilson_lower,
        posterior_alpha, posterior_beta, posterior_mean, posterior_lower, posterior_upper
    """
    rows = conn.execute(
        """
        SELECT
            image_sk,
            COUNT(*) AS shown_count,
            SUM(CASE WHEN was_selected THEN 1 ELSE 0 END) AS selected_count
        FROM fact_batch_ballot_image
        GROUP BY image_sk
        """
    ).fetchall()

    if not rows:
        logger.warning("No batch ballot data found")
        return {}

    # Beta prior: Beta(2, 8) encodes a prior expectation of ~20% selection rate
    # (slightly generous vs the 10% base rate of 5/50)
    prior_alpha = 2.0
    prior_beta = 8.0

    from scipy.stats import beta as beta_dist

    scores: dict[int, dict] = {}
    for image_sk, shown, selected in rows:
        shown = int(shown)
        selected = int(selected)

        # Raw selection rate
        sel_rate = selected / shown if shown > 0 else 0.0

        # Wilson lower bound (95% confidence)
        wilson = _wilson_lower(selected, shown)

        # Beta posterior
        post_alpha = prior_alpha + selected
        post_beta = prior_beta + (shown - selected)
        post_mean = post_alpha / (post_alpha + post_beta)
        post_lower = float(beta_dist.ppf(0.025, post_alpha, post_beta))
        post_upper = float(beta_dist.ppf(0.975, post_alpha, post_beta))

        scores[image_sk] = {
            "shown_count": shown,
            "selected_count": selected,
            "selection_rate": sel_rate,
            "wilson_lower": wilson,
            "posterior_alpha": post_alpha,
            "posterior_beta": post_beta,
            "posterior_mean": post_mean,
            "posterior_lower": post_lower,
            "posterior_upper": post_upper,
        }

    logger.info(f"Computed batch scores for {len(scores)} images")
    return scores


def compute_polarization(conn: duckdb.DuckDBPyConnection) -> dict[int, float]:
    """Compute polarization score per image: std dev of per-voter selection outcomes.

    Higher values mean more disagreement among voters about the image.
    """
    rows = conn.execute(
        """
        SELECT
            image_sk,
            STDDEV_POP(CASE WHEN was_selected THEN 1.0 ELSE 0.0 END) AS polarization
        FROM fact_batch_ballot_image
        GROUP BY image_sk
        HAVING COUNT(*) >= 2
        """
    ).fetchall()

    return {int(r[0]): float(r[1]) if r[1] is not None else 0.0 for r in rows}


def _wilson_lower(selected: int, shown: int, z: float = 1.96) -> float:
    """Wilson score lower bound for a binomial proportion."""
    if shown == 0:
        return 0.0
    p = selected / shown
    denominator = 1 + z * z / shown
    centre = p + z * z / (2 * shown)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * shown)) / shown)
    return (centre - spread) / denominator
