"""Fetch and extract photo metadata from ArtemisTimeline photos.js."""

import json
import re

from artemis_calendar.extract.download import DownloadResult, download_artifact


def fetch_photos_js(url: str) -> DownloadResult:
    """Download photos.js from ArtemisTimeline."""
    return download_artifact(url)


def extract_photo_data(js_content: bytes) -> list[dict]:
    """Extract PHOTO_DATA from photos.js content.

    The file is JavaScript that defines: var PHOTO_DATA = { photos: [...] };
    We strip the JS wrapper to extract the JSON array.
    """
    text = js_content.decode("utf-8")

    # Match the photos array inside PHOTO_DATA — keys may be quoted or unquoted
    match = re.search(r'"?photos"?\s*:\s*(\[.*\])', text, re.DOTALL)
    if not match:
        raise ValueError("Could not find photos array in photos.js")

    array_text = match.group(1)

    # The JS may have trailing commas which aren't valid JSON — clean them
    array_text = re.sub(r",\s*([\]}])", r"\1", array_text)

    # Handle unquoted keys: JS allows {key: value} but JSON requires {"key": value}
    # Match word characters before a colon that aren't inside quotes
    array_text = re.sub(r"(?<=[{,])\s*(\w+)\s*:", r' "\1":', array_text)

    return json.loads(array_text)
