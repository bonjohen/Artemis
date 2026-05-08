"""Tests for parse/ module parsers."""

import json

import pytest

from artemis_calendar.parse.category_parser import parse_category_index
from artemis_calendar.parse.leaderboard_parser import parse_batch_leaderboard, parse_elo_leaderboard, parse_vote_counts
from artemis_calendar.parse.vote_manifest_parser import parse_vote_manifest


class TestVoteManifestParser:
    def test_parses_valid_manifest(self):
        data = {
            "r2_base": "https://example.com",
            "items": [
                {"guid": "ART002-E-10001", "link": "https://example.com/1"},
                {"guid": "ART002-E-10002", "link": "https://example.com/2"},
            ],
        }
        meta, items = parse_vote_manifest(json.dumps(data).encode())
        assert len(items) == 2
        assert items[0]["guid"] == "ART002-E-10001"
        assert meta["r2_base"] == "https://example.com"
        assert "items" not in meta

    def test_missing_items_key_raises(self):
        data = {"r2_base": "https://example.com"}
        with pytest.raises(ValueError, match="Missing required key 'items'"):
            parse_vote_manifest(json.dumps(data).encode())


class TestCategoryParser:
    def test_parses_valid_categories(self):
        data = {
            "version": 1,
            "buckets": [
                {"key": "earth", "slug": "earth", "label": "Earth Views", "count": 100, "showcase": "guid1"},
            ],
        }
        cats = parse_category_index(json.dumps(data).encode())
        assert len(cats) == 1
        assert cats[0]["key"] == "earth"

    def test_missing_buckets_key_raises(self):
        data = {"version": 1}
        with pytest.raises(ValueError, match="Missing required key 'buckets'"):
            parse_category_index(json.dumps(data).encode())


class TestBatchLeaderboardParser:
    def test_parses_valid_response(self):
        data = {
            "results": [
                {"guid": "ART002-E-10001", "picks": 10, "shown": 100, "rate": 0.1, "wilson": 0.05},
            ]
        }
        entries = parse_batch_leaderboard(json.dumps(data).encode())
        assert len(entries) == 1
        assert entries[0]["guid"] == "ART002-E-10001"

    def test_missing_results_raises(self):
        data = {"status": "ok"}
        with pytest.raises(ValueError, match="Missing required key 'results'"):
            parse_batch_leaderboard(json.dumps(data).encode())


class TestEloLeaderboardParser:
    def test_parses_valid_response(self):
        data = {
            "results": [
                {"guid": "ART002-E-10001", "elo": 1200, "wins": 5, "losses": 3},
            ]
        }
        entries = parse_elo_leaderboard(json.dumps(data).encode())
        assert len(entries) == 1
        assert entries[0]["elo"] == 1200

    def test_missing_results_raises(self):
        data = {}
        with pytest.raises(ValueError, match="Missing required key 'results'"):
            parse_elo_leaderboard(json.dumps(data).encode())


class TestVoteCountsParser:
    def test_parses_valid_counts(self):
        data = {"count": 5000, "unique_picked": 3200}
        result = parse_vote_counts(json.dumps(data).encode())
        assert result["count"] == 5000
        assert result["unique_picked"] == 3200
