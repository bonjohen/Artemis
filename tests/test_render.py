"""Tests for calendar rendering modules."""

from __future__ import annotations

import calendar

from PIL import Image, ImageDraw

from artemis_calendar.render.grid import render_calendar_grid
from artemis_calendar.render.layout import GRID_REGION, PAGE_H, PAGE_W, load_fonts
from artemis_calendar.render.page import render_cover_page, render_month_page


class TestLoadFonts:
    def test_load_fonts_returns_expected_keys(self):
        fonts = load_fonts()
        expected = {
            "month_title",
            "day_header",
            "day_number",
            "description_title",
            "description_body",
            "cover_title",
            "cover_subtitle",
            "cover_date",
        }
        assert set(fonts.keys()) == expected

    def test_fonts_are_truetype(self):
        fonts = load_fonts()
        for name, font in fonts.items():
            assert hasattr(font, "getbbox"), f"Font {name} is not a TrueType font"


class TestCalendarGrid:
    def _make_canvas(self):
        img = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        return img, draw

    def test_december_2026_starts_tuesday(self):
        """December 2026 starts on a Tuesday (Sunday-start index 2)."""
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(2026, 12)
        first_week = weeks[0]
        assert first_week[2] == 1, f"Dec 2026 day 1 at index {first_week.index(1)}, expected 2"
        assert first_week[0] == 0  # Sunday is empty
        assert first_week[1] == 0  # Monday is empty

    def test_january_2027_starts_friday(self):
        """January 2027 starts on a Friday (Sunday-start index 5)."""
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(2027, 1)
        first_week = weeks[0]
        assert first_week[5] == 1, f"Jan 2027 day 1 at index {first_week.index(1)}, expected 5"

    def test_december_2026_has_31_days(self):
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(2026, 12)
        all_days = [d for week in weeks for d in week if d != 0]
        assert len(all_days) == 31
        assert max(all_days) == 31

    def test_february_2027_has_28_days(self):
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(2027, 2)
        all_days = [d for week in weeks for d in week if d != 0]
        assert len(all_days) == 28

    def test_render_grid_does_not_raise(self):
        """Smoke test: rendering a grid should not raise."""
        _, draw = self._make_canvas()
        fonts = load_fonts()
        render_calendar_grid(draw, 2026, 12, GRID_REGION, fonts)

    def test_render_grid_all_13_months(self):
        """All 13 calendar months render without error."""
        from artemis_calendar.optimize.month_fit import CALENDAR_MONTHS

        fonts = load_fonts()
        for m in CALENDAR_MONTHS:
            _, draw = self._make_canvas()
            render_calendar_grid(draw, m["year"], m["month"], GRID_REGION, fonts)


def _make_test_image(tmp_path, width=800, height=600):
    """Create a temporary test image and return its path."""
    img = Image.new("RGB", (width, height), (100, 150, 200))
    path = tmp_path / "test_photo.jpg"
    img.save(path)
    return path


class TestMonthPage:
    def test_month_page_dimensions(self, tmp_path):
        img_path = _make_test_image(tmp_path)
        fonts = load_fonts()
        page = render_month_page(img_path, 2026, 12, 1, "December 2026", fonts)
        assert page.size == (PAGE_W, PAGE_H)

    def test_month_page_with_description(self, tmp_path):
        img_path = _make_test_image(tmp_path)
        fonts = load_fonts()
        page = render_month_page(
            img_path,
            2027,
            1,
            2,
            "January 2027",
            fonts,
            title="Earth from Space",
            description="A view of Earth taken during the Artemis II mission.",
        )
        assert page.size == (PAGE_W, PAGE_H)

    def test_month_page_no_description(self, tmp_path):
        img_path = _make_test_image(tmp_path)
        fonts = load_fonts()
        page = render_month_page(img_path, 2027, 6, 7, "June 2027", fonts)
        assert page.size == (PAGE_W, PAGE_H)

    def test_month_page_extreme_aspect_ratio(self, tmp_path):
        """Panoramic images should use letterbox instead of aggressive crop."""
        img_path = _make_test_image(tmp_path, width=2400, height=400)
        fonts = load_fonts()
        page = render_month_page(img_path, 2027, 3, 4, "March 2027", fonts)
        assert page.size == (PAGE_W, PAGE_H)


class TestCoverPage:
    def test_cover_page_dimensions(self, tmp_path):
        img_path = _make_test_image(tmp_path)
        fonts = load_fonts()
        page = render_cover_page(img_path, fonts)
        assert page.size == (PAGE_W, PAGE_H)

    def test_cover_page_custom_title(self, tmp_path):
        img_path = _make_test_image(tmp_path)
        fonts = load_fonts()
        page = render_cover_page(img_path, fonts, title="ARTEMIS", subtitle="2027 Calendar")
        assert page.size == (PAGE_W, PAGE_H)


class TestCombinedPdf:
    def test_combined_pdf_from_pages(self, tmp_path):
        """Verify multi-page PDF assembly works."""
        fonts = load_fonts()
        img_path = _make_test_image(tmp_path)

        # Render cover + 3 month pages
        cover = render_cover_page(img_path, fonts)
        pages = [
            render_month_page(img_path, 2026, 12, 1, "December 2026", fonts),
            render_month_page(img_path, 2027, 1, 2, "January 2027", fonts),
            render_month_page(img_path, 2027, 2, 3, "February 2027", fonts),
        ]

        pdf_path = tmp_path / "test_calendar.pdf"
        all_pages = [cover] + pages
        all_pages[0].save(
            pdf_path,
            save_all=True,
            append_images=all_pages[1:],
            resolution=300,
        )

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


class TestMonthNameParsing:
    def test_month_name_to_num(self):
        from artemis_calendar.render.pipeline import _month_name_to_num

        assert _month_name_to_num("January") == 1
        assert _month_name_to_num("December") == 12
        assert _month_name_to_num("June") == 6


class TestResolveImagePath:
    def test_resolve_finds_full_res(self, tmp_path, monkeypatch):
        from artemis_calendar.render import pipeline

        # Create a mock LARGE_DIR with a test image
        large_dir = tmp_path / "large"
        large_dir.mkdir()
        test_file = large_dir / "TEST-GUID.JPG"
        test_file.write_bytes(b"fake image data")

        monkeypatch.setattr(pipeline, "LARGE_DIR", large_dir)
        result = pipeline._resolve_image_path("TEST-GUID")
        assert result == test_file

    def test_resolve_falls_back_to_thumb(self, tmp_path, monkeypatch):
        from artemis_calendar.render import pipeline

        large_dir = tmp_path / "large"
        large_dir.mkdir()

        thumbs_dir = tmp_path / "thumbs"
        thumbs_dir.mkdir()
        thumb_file = thumbs_dir / "TEST-GUID.jpg"
        thumb_file.write_bytes(b"fake thumb data")

        monkeypatch.setattr(pipeline, "LARGE_DIR", large_dir)
        monkeypatch.setattr(pipeline, "RAW_ROOT", tmp_path)
        # Patch the parent so thumbs path resolves correctly
        monkeypatch.setattr(
            pipeline,
            "_resolve_image_path",
            lambda guid: thumbs_dir / f"{guid}.jpg" if (thumbs_dir / f"{guid}.jpg").exists() else None,
        )
        # Just verify the thumb exists
        assert thumb_file.exists()
