"""Pairwise voting scores: Elo rating computation."""

from __future__ import annotations

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.pairwise")

DEFAULT_ELO = 1500.0
K_FACTOR = 32.0


def compute_elo_scores(conn: duckdb.DuckDBPyConnection) -> dict[int, dict]:
    """Compute Elo ratings from pairwise vote data.

    Returns dict keyed by image_sk with keys:
        elo_score, pairwise_wins, pairwise_losses
    """
    rows = conn.execute(
        """
        SELECT winner_image_sk, loser_image_sk
        FROM fact_pairwise_vote
        ORDER BY pairwise_vote_sk ASC
        """
    ).fetchall()

    if not rows:
        logger.warning("No pairwise vote data found")
        return {}

    # Track ratings, wins, and losses
    ratings: dict[int, float] = {}
    wins: dict[int, int] = {}
    losses: dict[int, int] = {}

    for winner_sk, loser_sk in rows:
        winner_sk = int(winner_sk)
        loser_sk = int(loser_sk)

        # Initialize if first appearance
        if winner_sk not in ratings:
            ratings[winner_sk] = DEFAULT_ELO
            wins[winner_sk] = 0
            losses[winner_sk] = 0
        if loser_sk not in ratings:
            ratings[loser_sk] = DEFAULT_ELO
            wins[loser_sk] = 0
            losses[loser_sk] = 0

        # Expected scores
        r_w = ratings[winner_sk]
        r_l = ratings[loser_sk]
        exp_w = 1.0 / (1.0 + 10.0 ** ((r_l - r_w) / 400.0))
        exp_l = 1.0 - exp_w

        # Update ratings
        ratings[winner_sk] = r_w + K_FACTOR * (1.0 - exp_w)
        ratings[loser_sk] = r_l + K_FACTOR * (0.0 - exp_l)

        wins[winner_sk] += 1
        losses[loser_sk] += 1

    scores = {
        img_sk: {
            "elo_score": ratings[img_sk],
            "pairwise_wins": wins[img_sk],
            "pairwise_losses": losses[img_sk],
        }
        for img_sk in ratings
    }

    logger.info(f"Computed Elo scores for {len(scores)} images from {len(rows)} pairwise votes")
    return scores
