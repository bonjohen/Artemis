"""Tests for the review package module."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from artemis_calendar.render.layout import PAGE_H, PAGE_W
from artemis_calendar.review.comparison import render_comparison_page
from artemis_calendar.review.contact_sheet import render_contact_sheet
from artemis_calendar.review.queries import (
    CandidateScore,
    ClusterAlternative,
    MonthImage,
)
from artemis_calendar.review.selection_report import render_selection_report


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


MONTH_LABELS = [
    "December 2026",
    "January 2027",
    "February 2027",
    "March 2027",
    "April 2027",
    "May 2027",
    "June 2027",
    "July 2027",
    "August 2027",
    "September 2027",
    "October 2027",
    "November 2027",
    "December 2027",
]


def _make_month_images(tmp_path: Path) -> list[MonthImage]:
    """Create 13 synthetic MonthImage objects with matching thumbnails."""
    images = []
    for i in range(13):
        guid = f"TEST{i:04d}"
        # Create a thumbnail file
        thumb = Image.new("RGB", (200, 150), (50 + i * 15, 100, 200 - i * 10))
        thumb.save(tmp_path / f"{guid}.jpg")

        images.append(
            MonthImage(
                sequence_number=i + 1,
                month_label=MONTH_LABELS[i],
                image_sk=14000 + i,
                source_image_id=guid,
                title=f"Test Image {i + 1}",
                description=f"Description for image {i + 1}.",
                month_fit_score=0.5 + i * 0.03,
                preference_score=0.8 - i * 0.02,
                brightness_score=0.4 + i * 0.04,
                contrast_score=0.5 + i * 0.02,
                saturation_score=0.3 + i * 0.05,
                dominant_color_json='{"r": 100, "g": 150, "b": 200}',
                cluster_id=i % 10,
                broad_appeal_score=0.6 + i * 0.01,
                uncertainty_score=0.1 + i * 0.005,
            )
        )
    return images


def _make_ranks() -> dict[int, int]:
    """Create synthetic rank mapping."""
    return {14000 + i: i * 100 + 1 for i in range(13)}


def _make_alternatives() -> dict[int, list[ClusterAlternative]]:
    """Create synthetic cluster alternatives."""
    alts = {}
    for i in range(13):
        sk = 14000 + i
        alts[sk] = [
            ClusterAlternative(
                image_sk=20000 + i * 10 + j,
                source_image_id=f"ALT{i:02d}{j:02d}",
                preference_score=0.7 - j * 0.05,
                broad_appeal_score=0.5,
            )
            for j in range(3)
        ]
    return alts


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


class TestContactSheet:
    def test_contact_sheet_dimensions(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        page = render_contact_sheet("method_b", 4.5, images, tmp_path, ranks)
        assert page.size == (PAGE_W, PAGE_H)

    def test_contact_sheet_is_rgb(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        page = render_contact_sheet("method_a", 3.0, images, tmp_path, ranks)
        assert page.mode == "RGB"

    def test_contact_sheet_no_thumbs(self, tmp_path):
        """Should render with placeholder boxes when thumbnails are missing."""
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        page = render_contact_sheet("method_c", 3.5, images, empty_dir, ranks)
        assert page.size == (PAGE_W, PAGE_H)

    def test_contact_sheet_save_png(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        page = render_contact_sheet("method_e", 5.0, images, tmp_path, ranks)
        out = tmp_path / "contact.png"
        page.save(out, dpi=(300, 300))
        assert out.exists()
        assert out.stat().st_size > 0


class TestSelectionReport:
    def test_selection_report_returns_pages(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        alts = _make_alternatives()
        pages = render_selection_report("method_b", 4.5, images, ranks, alts, tmp_path)
        assert len(pages) >= 1
        # 13 images at 3 per page = 5 pages
        assert len(pages) == 5

    def test_selection_report_page_dimensions(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        alts = _make_alternatives()
        pages = render_selection_report("method_b", 4.5, images, ranks, alts, tmp_path)
        for page in pages:
            assert page.size == (PAGE_W, PAGE_H)

    def test_selection_report_no_alternatives(self, tmp_path):
        """Should render even with no cluster alternatives."""
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        pages = render_selection_report("method_a", 3.0, images, ranks, {}, tmp_path)
        assert len(pages) >= 1

    def test_selection_report_no_thumbs(self, tmp_path):
        """Should render with placeholders when thumbnails are missing."""
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        pages = render_selection_report("method_d", 4.0, images, ranks, {}, empty_dir)
        assert len(pages) >= 1

    def test_selection_report_save_pdf(self, tmp_path):
        images = _make_month_images(tmp_path)
        ranks = _make_ranks()
        alts = _make_alternatives()
        pages = render_selection_report("method_b", 4.5, images, ranks, alts, tmp_path)
        out = tmp_path / "report.pdf"
        if len(pages) > 1:
            pages[0].save(out, save_all=True, append_images=pages[1:], resolution=300)
        else:
            pages[0].save(out, resolution=300)
        assert out.exists()
        assert out.stat().st_size > 0
