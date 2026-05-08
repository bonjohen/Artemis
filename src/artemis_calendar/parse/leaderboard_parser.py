"""Parse leaderboard API responses into score records."""

import json

from artemis_calendar.parse.vote_manifest_parser import _require_keys


def parse_batch_leaderboard(content: bytes) -> list[dict]:
    """Parse /top API response into list of score dicts.

    Each entry has: guid, picks, shown, rate, wilson.
    """
    data = json.loads(content)
    _require_keys(data, ["results"], "batch leaderboard")
    return data["results"]


def parse_elo_leaderboard(content: bytes) -> list[dict]:
    """Parse /elo-top API response into list of score dicts.

    Each entry has: guid, elo, wins, losses.
    """
    data = json.loads(content)
    _require_keys(data, ["results"], "elo leaderboard")
    return data["results"]


def parse_vote_counts(content: bytes) -> dict:
    """Parse /count API response.

    Returns dict with: count (ballots), unique_picked.
    """
    return json.loads(content)
