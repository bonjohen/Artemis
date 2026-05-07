"""Parse photos.js into structured photo records."""

import json
import re


def parse_photos_js(content: bytes) -> list[dict]:
    """Parse PHOTO_DATA from photos.js content into a list of photo dicts.

    The file is JavaScript: const PHOTO_DATA = { "photos": [...] };
    We strip the JS wrapper to get valid JSON.
    """
    text = content.decode("utf-8").strip()

    # Strip "const PHOTO_DATA = " prefix and trailing ";"
    text = re.sub(r"^(?:const|var|let)\s+PHOTO_DATA\s*=\s*", "", text)
    text = text.rstrip(";").strip()

    data = json.loads(text)
    return data["photos"]
