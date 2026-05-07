"""Parse category index.json into category records."""

import json


def parse_category_index(content: bytes) -> list[dict]:
    """Parse index.json into a list of category dicts.

    Format: {"version": 1, "buckets": [{key, slug, label, count, showcase}, ...]}
    """
    data = json.loads(content)
    return data.get("buckets", data if isinstance(data, list) else [])
