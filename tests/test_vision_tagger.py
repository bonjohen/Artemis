"""Tests for vision tagger, pipeline, and CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from PIL import Image

from artemis_calendar.vision.attributes import load_attribute_vocabulary
from artemis_calendar.vision.pipeline import _should_flag_for_review, run_vision_tagging
from artemis_calendar.vision.tagger import MockTagger, _parse_model_output


@pytest.fixture
def vocab():
    return load_attribute_vocabulary()


@pytest.fixture
def db():
    """In-memory DuckDB with all migrations applied."""
    conn = duckdb.connect(":memory:")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    for mf in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mf.read_text())
    return conn


@pytest.fixture
def db_with_images(db, tmp_path):
    """DB with 5 fake images and thumbnail files."""
    for i in range(1, 6):
        db.execute(
            """INSERT INTO dim_image (image_sk, source_image_id,
               vote_pool_flag, thumb_downloaded)
               VALUES (?, ?, true, true)""",
            [i, f"test_img_{i}"],
        )
        # Create dummy thumbnail
        img = Image.new("RGB", (100, 100), color=(i * 50, 100, 200))
        img.save(tmp_path / f"test_img_{i}.jpg")

    return db


class TestParseModelOutput:
    def test_parse_json(self, vocab):
        text = '{"earth": 0.95, "moon": 0.88, "deep_space": 0.92}'
        result = _parse_model_output(text, vocab)
        assert result["earth"] == 0.95
        assert result["moon"] == 0.88

    def test_parse_markdown_block(self, vocab):
        text = '```json\n{"earth": 0.95, "sun": 0.70}\n```'
        result = _parse_model_output(text, vocab)
        assert result["earth"] == 0.95
        assert result["sun"] == 0.70

    def test_parse_filters_unknown(self, vocab):
        text = '{"earth": 0.95, "mars": 0.80}'
        result = _parse_model_output(text, vocab)
        assert "earth" in result
        assert "mars" not in result

    def test_parse_clamps_range(self, vocab):
        text = '{"earth": 1.5, "moon": -0.3}'
        result = _parse_model_output(text, vocab)
        assert "earth" not in result  # > 1.0 rejected
        assert "moon" not in result  # < 0.0 rejected

    def test_parse_bad_json(self, vocab):
        result = _parse_model_output("not json at all", vocab)
        assert result == {}


class TestMockTagger:
    def test_deterministic(self, vocab):
        tagger = MockTagger(vocab)
        path = Path("test_image.jpg")
        r1 = tagger.tag_image(path)
        r2 = tagger.tag_image(path)
        assert r1 == r2

    def test_different_images_different_tags(self, vocab):
        tagger = MockTagger(vocab)
        r1 = tagger.tag_image(Path("image_a.jpg"))
        r2 = tagger.tag_image(Path("image_b.jpg"))
        assert r1 != r2

    def test_batch(self, vocab):
        tagger = MockTagger(vocab)
        paths = [Path(f"img_{i}.jpg") for i in range(5)]
        results = tagger.tag_batch(paths)
        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)


class TestReviewFlagging:
    def test_no_flag_normal(self, vocab):
        confidences = {"earth": 0.95, "moon": 0.88, "deep_space": 0.92}
        flag, reasons = _should_flag_for_review(confidences, vocab)
        assert not flag

    def test_flag_low_confidence(self, vocab):
        confidences = {"earth": 0.20, "moon": 0.10}
        flag, reasons = _should_flag_for_review(confidences, vocab)
        assert flag
        assert "low_overall_confidence" in reasons

    def test_flag_conflicting(self, vocab):
        confidences = {"surface": 0.90, "deep_space": 0.90, "earth": 0.85}
        flag, reasons = _should_flag_for_review(confidences, vocab)
        assert flag
        assert "conflicting_surface_and_deep_space" in reasons

    def test_flag_unusual_media(self, vocab):
        confidences = {"diagram": 0.85, "earth": 0.90, "moon": 0.80}
        flag, reasons = _should_flag_for_review(confidences, vocab)
        assert flag
        assert any("diagram" in r for r in reasons)


class TestVisionPipeline:
    def test_pipeline_with_mock(self, db_with_images, tmp_path, vocab):
        tagger = MockTagger(vocab)

        summary = run_vision_tagging(
            db_with_images,
            tagger=tagger,
            vocab=vocab,
            thumb_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        assert summary["images_processed"] == 5
        assert summary["attributes_written"] > 0

        # Check output file
        output_path = Path(summary["output_path"])
        assert output_path.exists()
        records = json.loads(output_path.read_text())
        assert len(records) == 5
        assert all("attributes" in r for r in records)
        assert all("derived_labels" in r for r in records)
        assert all("review_flag" in r for r in records)

    def test_pipeline_changed_only(self, db_with_images, tmp_path, vocab):
        tagger = MockTagger(vocab)

        # First run
        run_vision_tagging(
            db_with_images, tagger=tagger, vocab=vocab,
            thumb_dir=tmp_path, output_dir=tmp_path / "out1",
        )

        # Second run with changed_only — should skip all
        summary = run_vision_tagging(
            db_with_images, tagger=tagger, vocab=vocab,
            thumb_dir=tmp_path, output_dir=tmp_path / "out2",
            changed_only=True,
        )
        assert summary["images_processed"] == 0

    def test_pipeline_with_limit(self, db_with_images, tmp_path, vocab):
        tagger = MockTagger(vocab)
        summary = run_vision_tagging(
            db_with_images, tagger=tagger, vocab=vocab,
            thumb_dir=tmp_path, output_dir=tmp_path / "out",
            limit=2,
        )
        assert summary["images_processed"] == 2

    def test_db_records_written(self, db_with_images, tmp_path, vocab):
        tagger = MockTagger(vocab)
        run_vision_tagging(
            db_with_images, tagger=tagger, vocab=vocab,
            thumb_dir=tmp_path, output_dir=tmp_path / "out",
        )

        count = db_with_images.execute(
            "SELECT count(*) FROM feature_image_attribute"
        ).fetchone()[0]
        assert count > 0

        # Check that accepted flags are set correctly
        accepted = db_with_images.execute(
            "SELECT count(*) FROM feature_image_attribute WHERE is_accepted = true"
        ).fetchone()[0]
        assert accepted > 0
