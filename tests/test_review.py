"""Tests for the review package module."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from artemis_calendar.render.layout import PAGE_H, PAGE_W
from artemis_calendar.review.comparison import render_comparison_page
from artemis_calendar.review.queries import CandidateScore


def _make_candidates(n: int = 5) -> list[CandidateScore]:
    """Create synthetic CandidateScore objects for testing."""
    names = ["method_a", "method_b", "method_c", "method_d", "method_e"]
    return [
        CandidateScore(
            candidate_name=names[i],
            cover_image_sk=13775 + i,
            objective_score=3.0 + i * 0.5,
            popularity_score=8.0 - i * 0.3,
            diversity_score=0.5 + i * 0.1,
            month_fit_score=5.0 + i * 0.2,
            cover_fit_score=0.6 + i * 0.05,
            redundancy_penalty=0.3 - i * 0.02,
            uncertainty_penalty=1.0 - i * 0.1,
        )
        for i in range(n)
    ]


def _make_thumb(tmp_path: Path, name: str) -> Path:
    """Create a small test thumbnail."""
    img = Image.new("RGB", (200, 150), (100, 150, 200))
    path = tmp_path / f"{name}.jpg"
    img.save(path)
    return path


class TestCandidateScore:
    def test_dataclass_fields(self):
        c = _make_candidates(1)[0]
        assert c.candidate_name == "method_a"
        assert isinstance(c.objective_score, float)
        assert isinstance(c.cover_image_sk, int)

    def test_make_candidates_returns_five(self):
        candidates = _make_candidates()
        assert len(candidates) == 5


class TestComparisonPage:
    def test_comparison_page_dimensions(self, tmp_path):
        candidates = _make_candidates()
        thumb_paths = {c.candidate_name: _make_thumb(tmp_path, c.candidate_name) for c in candidates}
        page = render_comparison_page(candidates, thumb_paths)
        assert page.size == (PAGE_W, PAGE_H)

    def test_comparison_page_no_thumbs(self, tmp_path):
        """Should render even when no thumbnail files exist."""
        candidates = _make_candidates()
        thumb_paths = {c.candidate_name: tmp_path / "nonexistent.jpg" for c in candidates}
        page = render_comparison_page(candidates, thumb_paths)
        assert page.size == (PAGE_W, PAGE_H)

    def test_comparison_page_single_candidate(self, tmp_path):
        """Should handle a single candidate gracefully."""
        candidates = _make_candidates(1)
        thumb_paths = {candidates[0].candidate_name: _make_thumb(tmp_path, "method_a")}
        page = render_comparison_page(candidates, thumb_paths)
        assert page.size == (PAGE_W, PAGE_H)

    def test_comparison_page_empty(self):
        """Should return a blank page for zero candidates."""
        page = render_comparison_page([], {})
        assert page.size == (PAGE_W, PAGE_H)

    def test_comparison_page_is_rgb(self, tmp_path):
        candidates = _make_candidates(3)
        thumb_paths = {c.candidate_name: _make_thumb(tmp_path, c.candidate_name) for c in candidates}
        page = render_comparison_page(candidates, thumb_paths)
        assert page.mode == "RGB"

    def test_comparison_page_save_png(self, tmp_path):
        """Should save as PNG without error."""
        candidates = _make_candidates()
        thumb_paths = {c.candidate_name: _make_thumb(tmp_path, c.candidate_name) for c in candidates}
        page = render_comparison_page(candidates, thumb_paths)
        out = tmp_path / "comparison.png"
        page.save(out, dpi=(300, 300))
        assert out.exists()
        assert out.stat().st_size > 0
