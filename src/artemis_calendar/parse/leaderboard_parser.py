"""Parse leaderboard API responses into score records."""

import json


def parse_batch_leaderboard(content: bytes) -> list[dict]:
    """Parse /top API response into list of score dicts.

    Each entry has: guid, picks, shown, rate, wilson.
    """
    data = json.loads(content)
    return data.get("results", [])


def parse_elo_leaderboard(content: bytes) -> list[dict]:
    """Parse /elo-top API response into list of score dicts.

    Each entry has: guid, elo, wins, losses.
    """
    data = json.loads(content)
    return data.get("results", [])


def parse_vote_counts(content: bytes) -> dict:
    """Parse /count API response.

    Returns dict with: count (ballots), unique_picked.
    """
    return json.loads(content)
