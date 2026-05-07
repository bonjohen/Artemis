"""Source manifest reader — parses YAML manifest into structured entries."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ManifestEntry:
    source_name: str
    source_type: str
    source_url: str
    expected_format: str
    refresh_frequency: str = "manual"
    notes: str | None = None


def load_manifest(manifest_path: Path | str) -> list[ManifestEntry]:
    """Load and validate source manifest, returning all entries."""
    path = Path(manifest_path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "sources" not in data:
        raise ValueError(f"Manifest at {path} missing 'sources' key")

    entries = []
    for i, raw in enumerate(data["sources"]):
        required = {"source_name", "source_type", "source_url", "expected_format"}
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"Manifest entry {i} missing required fields: {missing}")
        entries.append(ManifestEntry(**{k: raw.get(k) for k in ManifestEntry.__dataclass_fields__}))

    return entries
