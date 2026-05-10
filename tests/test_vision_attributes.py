"""Tests for vision attribute vocabulary loading, validation, and derived labels."""

from __future__ import annotations

import textwrap
from pathlib import Path

import duckdb
import pytest

from artemis_calendar.vision.attributes import (
    AttributeVocabulary,
    load_attribute_vocabulary,
)
from artemis_calendar.vision.loader import seed_attribute_vocabulary, write_image_attributes


@pytest.fixture
def vocab() -> AttributeVocabulary:
    """Load the real attribute vocabulary from config."""
    return load_attribute_vocabulary()


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal test config."""
    config = tmp_path / "attrs.yaml"
    config.write_text(
        textwrap.dedent("""\
        thresholds:
          accepted: 0.80
          tentative: 0.50
        base_attributes:
          - code: earth
            label: Earth
            description: Earth visible
            type: celestial_body
          - code: moon
            label: Moon
            description: Moon visible
            type: celestial_body
          - code: sun
            label: Sun
            description: Sun visible
            type: celestial_body
        derived_attributes:
          - code: earth_and_moon
            label: Earth and Moon
            description: Both visible
            rule:
              all_of: [earth, moon]
          - code: earth_only
            label: Earth Only
            description: Earth without Moon or Sun
            rule:
              all_of: [earth]
              none_of: [moon, sun]
    """)
    )
    return config


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with migration 009 applied."""
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    sql = (migrations_dir / "009_create_vision_and_voting_block_tables.sql").read_text()
    conn.execute(sql)
    return conn


class TestAttributeLoading:
    def test_load_real_config(self, vocab: AttributeVocabulary) -> None:
        assert len(vocab.base_attributes) >= 20
        assert len(vocab.derived_attributes) >= 4
        assert "earth" in vocab.base_codes
        assert "earth_and_moon" in vocab.derived_codes

    def test_load_tmp_config(self, tmp_config: Path) -> None:
        v = load_attribute_vocabulary(tmp_config)
        assert v.base_codes == {"earth", "moon", "sun"}
        assert v.derived_codes == {"earth_and_moon", "earth_only"}

    def test_all_codes(self, vocab: AttributeVocabulary) -> None:
        assert vocab.all_codes == vocab.base_codes | vocab.derived_codes

    def test_get_attribute(self, vocab: AttributeVocabulary) -> None:
        attr = vocab.get_attribute("earth")
        assert attr is not None
        assert attr.label == "Earth"

        derived = vocab.get_attribute("earth_and_moon")
        assert derived is not None

        assert vocab.get_attribute("nonexistent") is None

    def test_duplicate_code_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yaml"
        config.write_text(
            textwrap.dedent("""\
            thresholds: {accepted: 0.80, tentative: 0.50}
            base_attributes:
              - code: earth
                label: Earth
                description: x
                type: celestial_body
              - code: earth
                label: Earth2
                description: y
                type: celestial_body
            derived_attributes: []
        """)
        )
        with pytest.raises(ValueError, match="Duplicate"):
            load_attribute_vocabulary(config)

    def test_bad_derived_reference_raises(self, tmp_path: Path) -> None:
        config = tmp_path / "bad2.yaml"
        config.write_text(
            textwrap.dedent("""\
            thresholds: {accepted: 0.80, tentative: 0.50}
            base_attributes:
              - code: earth
                label: Earth
                description: x
                type: celestial_body
            derived_attributes:
              - code: earth_and_mars
                label: Earth and Mars
                description: x
                rule:
                  all_of: [earth, mars]
        """)
        )
        with pytest.raises(ValueError, match="mars"):
            load_attribute_vocabulary(config)


class TestConfidenceClassification:
    def test_accepted(self, vocab: AttributeVocabulary) -> None:
        assert vocab.classify_confidence(0.95) == "accepted"
        assert vocab.classify_confidence(0.80) == "accepted"

    def test_tentative(self, vocab: AttributeVocabulary) -> None:
        assert vocab.classify_confidence(0.79) == "tentative"
        assert vocab.classify_confidence(0.50) == "tentative"

    def test_rejected(self, vocab: AttributeVocabulary) -> None:
        assert vocab.classify_confidence(0.49) == "rejected"
        assert vocab.classify_confidence(0.0) == "rejected"


class TestDerivedLabels:
    def test_earth_and_moon(self, tmp_config: Path) -> None:
        v = load_attribute_vocabulary(tmp_config)
        labels = v.compute_derived_labels({"earth": 0.95, "moon": 0.90, "sun": 0.10})
        assert "earth_and_moon" in labels
        assert "earth_only" not in labels  # moon is present

    def test_earth_only(self, tmp_config: Path) -> None:
        v = load_attribute_vocabulary(tmp_config)
        labels = v.compute_derived_labels({"earth": 0.95, "moon": 0.10, "sun": 0.05})
        assert "earth_only" in labels
        assert "earth_and_moon" not in labels

    def test_nothing_derived(self, tmp_config: Path) -> None:
        v = load_attribute_vocabulary(tmp_config)
        labels = v.compute_derived_labels({"earth": 0.30, "moon": 0.10, "sun": 0.05})
        assert labels == []

    def test_earth_only_blocked_by_tentative_moon(self, tmp_config: Path) -> None:
        """earth_only requires moon < tentative (0.50)."""
        v = load_attribute_vocabulary(tmp_config)
        labels = v.compute_derived_labels({"earth": 0.95, "moon": 0.55, "sun": 0.05})
        assert "earth_only" not in labels

    def test_accepted_base_labels(self, tmp_config: Path) -> None:
        v = load_attribute_vocabulary(tmp_config)
        labels = v.compute_accepted_base_labels({"earth": 0.95, "moon": 0.40, "sun": 0.85})
        assert set(labels) == {"earth", "sun"}


class TestDatabaseIntegration:
    def test_seed_vocabulary(self, db: duckdb.DuckDBPyConnection) -> None:
        count = seed_attribute_vocabulary(db)
        assert count > 0

        rows = db.execute("SELECT count(*) FROM dim_image_attribute").fetchone()[0]
        assert rows == count

        # Check a specific attribute
        row = db.execute(
            "SELECT attribute_label, is_derived FROM dim_image_attribute WHERE attribute_code = 'earth'"
        ).fetchone()
        assert row[0] == "Earth"
        assert row[1] is False

        # Check a derived attribute
        row = db.execute(
            "SELECT is_derived FROM dim_image_attribute WHERE attribute_code = 'earth_and_moon'"
        ).fetchone()
        assert row[0] is True

    def test_seed_idempotent(self, db: duckdb.DuckDBPyConnection) -> None:
        count1 = seed_attribute_vocabulary(db)
        count2 = seed_attribute_vocabulary(db)
        assert count1 == count2
        rows = db.execute("SELECT count(*) FROM dim_image_attribute").fetchone()[0]
        assert rows == count1

    def test_write_image_attributes(self, db: duckdb.DuckDBPyConnection) -> None:
        vocab = load_attribute_vocabulary()
        confidences = {"earth": 0.95, "moon": 0.88, "sun": 0.10, "deep_space": 0.92}

        count = write_image_attributes(
            db,
            image_sk=100,
            base_confidences=confidences,
            vocab=vocab,
            model_name="qwen2.5-vl-7b",
            model_version="test",
            run_id="test-run",
        )

        # 4 base + derived labels (earth_and_moon should fire)
        assert count >= 4

        # Check accepted flag
        accepted = db.execute(
            "SELECT count(*) FROM feature_image_attribute WHERE image_sk = 100 AND is_accepted = true"
        ).fetchone()[0]
        assert accepted >= 3  # earth, moon, deep_space are all accepted

        # Check derived label exists
        derived = db.execute(
            "SELECT count(*) FROM feature_image_attribute WHERE image_sk = 100 AND attribute_code = 'earth_and_moon'"
        ).fetchone()[0]
        assert derived == 1
