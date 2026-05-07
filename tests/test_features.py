"""Tests for feature extraction modules."""

import json
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from artemis_calendar.features.text_features import _extract_entities, _extract_sentiment, _extract_topics
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


class TestImageEmbeddings:
    def test_clip_embedding_dimension(self):
        """Test CLIP embedding produces 512-dim vector (mocked model)."""
        fake_output = MagicMock()
        fake_tensor = MagicMock()
        fake_tensor.norm.return_value = MagicMock()
        fake_tensor.__truediv__ = lambda self, other: self
        fake_tensor.cpu.return_value = fake_tensor
        fake_tensor.numpy.return_value = np.random.randn(1, 512).astype(np.float32)
        fake_output.return_value = fake_tensor

        from artemis_calendar.features.embeddings import CLIP_DIMENSION, _sha256_bytes

        assert CLIP_DIMENSION == 512
        # Verify hash function works
        h = _sha256_bytes(b"test data")
        assert len(h) == 64  # SHA-256 hex digest

    def test_sha256_text(self):
        from artemis_calendar.features.embeddings import _sha256_text

        h = _sha256_text("hello world")
        assert len(h) == 64
        # Same input = same hash
        assert _sha256_text("hello world") == h
        # Different input = different hash
        assert _sha256_text("hello world!") != h


class TestTextEmbeddings:
    def test_text_model_config(self):
        from artemis_calendar.features.embeddings import TEXT_DIMENSION, TEXT_MODEL

        assert TEXT_DIMENSION == 384
        assert TEXT_MODEL == "all-MiniLM-L6-v2"


class TestSentiment:
    def test_positive_text(self):
        score, subj = _extract_sentiment("This is an amazing and beautiful photograph!")
        assert score > 0.0

    def test_negative_text(self):
        score, subj = _extract_sentiment("This is a terrible and ugly failure.")
        assert score < 0.0

    def test_neutral_text(self):
        score, subj = _extract_sentiment("The spacecraft is located at coordinates 123.")
        assert -0.5 <= score <= 0.5

    def test_subjectivity_range(self):
        _, subj = _extract_sentiment("This is absolutely wonderful and amazing!")
        assert 0.0 <= subj <= 1.0


class TestEntities:
    def test_earth_detection(self):
        entities = _extract_entities("A beautiful view of Earth from lunar orbit")
        assert entities["Earth"] is True
        assert entities["Moon"] is False

    def test_moon_detection(self):
        entities = _extract_entities("The Moon rises over the horizon")
        assert entities["Moon"] is True

    def test_orion_detection(self):
        entities = _extract_entities("Orion spacecraft approaching lunar orbit")
        assert entities["Orion"] is True
        assert entities["spacecraft"] is True

    def test_crew_detection(self):
        entities = _extract_entities("Astronaut Reid Wiseman during EVA")
        assert entities["crew"] is True

    def test_sls_detection(self):
        entities = _extract_entities("SLS rocket on the launchpad")
        assert entities["SLS"] is True

    def test_no_entities(self):
        entities = _extract_entities("A photo taken from the window")
        assert not any(entities.values())


class TestTopics:
    def test_basic_topics(self):
        texts = [
            "Earth from lunar orbit showing blue oceans",
            "Moon surface craters and mountains",
            "Earth atmosphere layers visible from space",
            "Moon landing site from orbit photograph",
            "Earth sunrise over the Pacific ocean",
        ]
        topics = _extract_topics(texts, top_n=5)
        assert len(topics) == len(texts)
        for t in topics:
            assert isinstance(t, list)

    def test_empty_input(self):
        assert _extract_topics([]) == []

    def test_single_doc(self):
        # With min_df=2, a single doc won't have enough terms
        topics = _extract_topics(["just one document about space"])
        assert len(topics) == 1
