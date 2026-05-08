"""Parse vote manifest.json into image GUID records."""

import json


def _require_keys(data: dict, keys: list[str], context: str) -> None:
    """Validate that all required keys are present in data."""
    for k in keys:
        if k not in data:
            raise ValueError(f"Missing required key '{k}' in {context}")


def parse_vote_manifest(content: bytes) -> tuple[dict, list[dict]]:
    """Parse manifest.json, returning (metadata, items).

    metadata contains r2_base, thumb_path, nasa_detail_base, etc.
    items is a list of dicts with guid and link fields.
    """
    data = json.loads(content)
    _require_keys(data, ["items"], "vote manifest")
    items = data["items"]
    metadata = {k: v for k, v in data.items() if k != "items"}
    return metadata, items
