"""Parse vote manifest.json into image GUID records."""

import json


def parse_vote_manifest(content: bytes) -> tuple[dict, list[dict]]:
    """Parse manifest.json, returning (metadata, items).

    metadata contains r2_base, thumb_path, nasa_detail_base, etc.
    items is a list of dicts with guid and link fields.
    """
    data = json.loads(content)
    items = data.get("items", [])
    metadata = {k: v for k, v in data.items() if k != "items"}
    return metadata, items
