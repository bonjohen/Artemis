"""Tests for feature extraction modules."""

import json

import pytest
from PIL import Image

from artemis_calendar.features.visual import (
    _compute_brightness,
    _compute_contrast,
    _compute_dominant_colors,
    _compute_orientation,
    _compute_saturation,
    extract_visual_features_for_image,
)


@pytest.fixture
def landscape_image():
    """A 200x100 landscape image with known colors."""
    img = Image.new("RGB", (200, 100), color=(255, 128, 64))
    return img


@pytest.fixture
def portrait_image():
    """A 100x200 portrait image."""
    return Image.new("RGB", (100, 200), color=(64, 128, 255))


@pytest.fixture
def square_image():
    """A 100x100 square image."""
    return Image.new("RGB", (100, 100), color=(128, 128, 128))


class TestOrientation:
    def test_landscape(self):
        assert _compute_orientation(200, 100) == "landscape"

    def test_portrait(self):
        assert _compute_orientation(100, 200) == "portrait"

    def test_square(self):
        assert _compute_orientation(100, 100) == "square"

    def test_near_square_landscape(self):
        # 1.04 ratio — within square tolerance
        assert _compute_orientation(104, 100) == "square"

    def test_near_square_portrait(self):
        assert _compute_orientation(100, 104) == "square"


class TestBrightness:
    def test_range(self, landscape_image):
        b = _compute_brightness(landscape_image)
        assert 0.0 <= b <= 1.0

    def test_black_is_dark(self):
        black = Image.new("RGB", (50, 50), color=(0, 0, 0))
        assert _compute_brightness(black) < 0.1

    def test_white_is_bright(self):
        white = Image.new("RGB", (50, 50), color=(255, 255, 255))
        assert _compute_brightness(white) > 0.9


class TestContrast:
    def test_range(self, landscape_image):
        c = _compute_contrast(landscape_image)
        assert 0.0 <= c <= 1.0

    def test_uniform_is_zero(self):
        uniform = Image.new("RGB", (50, 50), color=(128, 128, 128))
        assert _compute_contrast(uniform) < 0.01


class TestSaturation:
    def test_range(self, landscape_image):
        s = _compute_saturation(landscape_image)
        assert 0.0 <= s <= 1.0

    def test_gray_is_low(self):
        gray = Image.new("RGB", (50, 50), color=(128, 128, 128))
        assert _compute_saturation(gray) < 0.05


class TestDominantColors:
    def test_structure(self, landscape_image):
        colors = _compute_dominant_colors(landscape_image, k=3)
        assert len(colors) >= 1
        for c in colors:
            assert "r" in c and "g" in c and "b" in c
            assert "proportion" in c
            assert 0 <= c["r"] <= 255
            assert 0 <= c["g"] <= 255
            assert 0 <= c["b"] <= 255
            assert 0.0 <= c["proportion"] <= 1.0

    def test_uniform_color_dominant(self):
        red = Image.new("RGB", (50, 50), color=(255, 0, 0))
        colors = _compute_dominant_colors(red, k=3)
        # With a uniform image, the dominant color should be very close to red
        assert colors[0]["r"] > 200
        assert colors[0]["g"] < 50
        assert colors[0]["b"] < 50


class TestExtractVisualFeatures:
    def test_full_extraction(self, landscape_image):
        features = extract_visual_features_for_image(landscape_image)
        assert features["orientation"] == "landscape"
        assert features["aspect_ratio"] == 2.0
        assert 0.0 <= features["brightness_score"] <= 1.0
        assert 0.0 <= features["contrast_score"] <= 1.0
        assert 0.0 <= features["saturation_score"] <= 1.0

        colors = json.loads(features["dominant_color_json"])
        assert isinstance(colors, list)
        assert len(colors) >= 1

    def test_portrait_extraction(self, portrait_image):
        features = extract_visual_features_for_image(portrait_image)
        assert features["orientation"] == "portrait"
        assert features["aspect_ratio"] == 0.5

    def test_square_extraction(self, square_image):
        features = extract_visual_features_for_image(square_image)
        assert features["orientation"] == "square"
        assert features["aspect_ratio"] == 1.0
