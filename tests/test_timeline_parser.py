"""Tests for the timeline photos.js parser."""

from artemis_calendar.parse.timeline_parser import parse_photos_js

SAMPLE_PHOTOS_JS = b"""
const PHOTO_DATA = {
  "photos": [
    {
      "time": "2026-03-27 19:10:00",
      "file": "NHQ202603270002~large.jpg",
      "photographer": "NASA/Joel Kowsky",
      "location": "Kennedy Space Center",
      "camera": "",
      "settings": "",
      "spacecraft": false,
      "batch": 0,
      "title": "SLS Glows at Sunset on Pad 39B",
      "flickr_desc": "A rocket at sunset.",
      "enabled": false
    },
    {
      "time": "2026-04-02 08:15:52",
      "file": "55224434205_228b6d3cee_o.jpg",
      "photographer": "Artemis II Crew",
      "location": "Orion Spacecraft",
      "camera": "NIKON D5",
      "settings": "100mm f/14.0 1/320s ISO 400",
      "spacecraft": true,
      "batch": 1,
      "title": "A Crescent View of Home",
      "flickr_desc": "A crescent Earth photographed from Orion.",
      "enabled": true,
      "camera_id": "d5a"
    }
  ]
};
"""


def test_parse_photos_js():
    photos = parse_photos_js(SAMPLE_PHOTOS_JS)
    assert len(photos) == 2
    assert photos[0]["title"] == "SLS Glows at Sunset on Pad 39B"
    assert photos[0]["spacecraft"] is False
    assert photos[0]["enabled"] is False
    assert photos[1]["title"] == "A Crescent View of Home"
    assert photos[1]["spacecraft"] is True
    assert photos[1]["camera_id"] == "d5a"


def test_parse_photos_js_empty():
    content = b'const PHOTO_DATA = { "photos": [] };'
    photos = parse_photos_js(content)
    assert photos == []
