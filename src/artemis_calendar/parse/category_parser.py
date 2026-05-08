"""Parse category index.json into category records."""

import json

from artemis_calendar.parse.vote_manifest_parser import _require_keys


def parse_category_index(content: bytes) -> list[dict]:
    """Parse index.json into a list of category dicts.

    Format: {"version": 1, "buckets": [{key, slug, label, count, showcase}, ...]}
    """
    data = json.loads(content)
    _require_keys(data, ["buckets"], "category index.json")
    return data["buckets"]
