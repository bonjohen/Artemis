"""Fetch voting data from ArtemisTimeline vote system and API."""

import json

from artemis_calendar.extract.download import DownloadResult, download_artifact


def fetch_vote_manifest(url: str) -> DownloadResult:
    """Download vote/manifest.json."""
    return download_artifact(url)


def parse_vote_manifest(content: bytes) -> dict:
    """Parse manifest.json into structured data."""
    return json.loads(content)


def fetch_category_index(url: str) -> DownloadResult:
    """Download vote/c/index.json."""
    return download_artifact(url)


def parse_category_index(content: bytes) -> list[dict]:
    """Parse index.json category array."""
    return json.loads(content)


def fetch_leaderboard(url: str) -> DownloadResult:
    """Download a leaderboard API endpoint."""
    return download_artifact(url)


def parse_leaderboard(content: bytes) -> dict:
    """Parse leaderboard API JSON response."""
    return json.loads(content)


def fetch_vote_counts(url: str) -> DownloadResult:
    """Download /count API endpoint."""
    return download_artifact(url)


def parse_vote_counts(content: bytes) -> dict:
    """Parse vote count response."""
    return json.loads(content)
