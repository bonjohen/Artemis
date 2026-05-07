# Calendar Rendering (Phase C4) — Implementation Plan

**Source document:** `docs/calendar_design.md` (sections 8–15)

## Work Queue Instructions

### State Transitions

Open  ──>  Started  ──>  Completed
              │
              └──>  Blocked  ──>  Started  ──>  Completed

- **Open**: Not yet begun.
- **Started**: Actively in progress. Record the start datetime (PST).
- **Completed**: Done and verified. Record the completion datetime (PST).
- **Blocked**: Cannot proceed; note the blocker in the description.

### Commit Protocol

1. Work through all tasks in a phase.
2. When every task reaches Completed, write the Phase Summary.
3. Stage and commit all changes for the phase. Do not push.
4. Proceed immediately to the next phase.

## Technology Stack (Additive)

| Concern | Choice |
|---|---|
| Image rendering | Pillow (already installed via `[ml]` extras) |
| PDF output | Pillow `Image.save("x.pdf", save_all=True, append_images=[...])` |
| Calendar math | Python stdlib `calendar` module |
| Font | Segoe UI from `C:\Windows\Fonts\segoeui.ttf` / `segoeuib.ttf` |
| Resolution | 2550x3300 px (300 DPI on 8.5x11 inch) |

## Phase 1: Layout Constants and Calendar Grid

**Goal:** Render correct calendar grids with day-of-week alignment for all 13 months.
**Depends on:** Nothing (first phase).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-07 02:00 PM | 2026-05-07 02:01 PM | Create `src/artemis_calendar/render/__init__.py` (empty package init) |
| 1.2 | Completed | 2026-05-07 02:01 PM | 2026-05-07 02:03 PM | Create `src/artemis_calendar/render/layout.py` — page constants (PAGE_W, PAGE_H, MARGIN, regions), font paths, `load_fonts()` |
| 1.3 | Completed | 2026-05-07 02:03 PM | 2026-05-07 02:05 PM | Create `src/artemis_calendar/render/grid.py` — `render_calendar_grid(draw, year, month, region, fonts)` using `calendar.monthcalendar()` with Sunday start |
| 1.4 | Completed | 2026-05-07 02:05 PM | 2026-05-07 02:08 PM | Add grid unit tests to `tests/test_render.py` — verify Dec 2026 starts Tuesday, Jan 2027 starts Friday, correct day counts |
| 1.5 | Completed | 2026-05-07 02:08 PM | 2026-05-07 02:10 PM | Run `pytest` and `ruff check && ruff format --check` — fix until green |

### Phase 1 Summary

- **Changes:** Created `render/` package with `__init__.py`, `layout.py` (page constants, font loading), `grid.py` (calendar grid renderer). Added `tests/test_render.py` with 8 tests. All 86 tests pass, ruff clean on new files.
- **Changes hosted at:** local
- **Commit:** `Add calendar rendering layout constants and grid renderer`

## Phase 2: Page Composition

**Goal:** Render complete monthly pages and cover pages from image files.
**Depends on:** Phase 1 (layout constants and grid renderer).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-07 02:12 PM | 2026-05-07 02:16 PM | Create `src/artemis_calendar/render/page.py` — `render_month_page()` (white canvas, center-crop image to top half, month title, grid, optional description) |
| 2.2 | Completed | 2026-05-07 02:16 PM | 2026-05-07 02:16 PM | Add `render_cover_page()` to `page.py` — full-bleed image, dark overlay band, title text ("FARTHER", "2027 Calendar", date range) |
| 2.3 | Completed | 2026-05-07 02:16 PM | 2026-05-07 02:19 PM | Add page composition tests — verify 2550x3300 output, description, extreme aspect, cover |
| 2.4 | Completed | 2026-05-07 02:19 PM | 2026-05-07 02:20 PM | Run `pytest` and `ruff check && ruff format --check` — fix until green |

### Phase 2 Summary

- **Changes:** Created `render/page.py` with `render_month_page()` (center-crop, month title, grid, optional description) and `render_cover_page()` (full-bleed, dark overlay, title text). Added 6 page composition tests. All 92 tests pass, ruff clean.
- **Changes hosted at:** local
- **Commit:** `Add monthly page and cover page renderers`

## Phase 3: Download, Pipeline, and CLI

**Goal:** End-to-end calendar rendering from warehouse data to combined PDF.
**Depends on:** Phase 2 (page composition).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 3.1 | Completed | 2026-05-07 02:22 PM | 2026-05-07 02:22 PM | Add `OUTPUT_ROOT = DATA_ROOT / "output"` to `src/artemis_calendar/config/settings.py` |
| 3.2 | Completed | 2026-05-07 02:22 PM | 2026-05-07 02:26 PM | Add `download_candidate_images(conn, candidate_name, run_id)` to `src/artemis_calendar/extract/images.py` — query 13 GUIDs from mart tables, download missing full-res images from NASA JSC with 1.0s rate limit |
| 3.3 | Completed | 2026-05-07 02:26 PM | 2026-05-07 02:30 PM | Create `src/artemis_calendar/render/pipeline.py` — `render_calendar(conn, candidate_name, run_id)` orchestrator: query data, download images, render all pages, combine PDF |
| 3.4 | Completed | 2026-05-07 02:30 PM | 2026-05-07 02:30 PM | Update `src/artemis_calendar/render/__init__.py` to expose `render_calendar` |
| 3.5 | Completed | 2026-05-07 02:30 PM | 2026-05-07 02:33 PM | Add `render-calendar` subcommand to `src/artemis_calendar/cli.py` — `--candidate` (default method_b), `--run-id` (default latest), `--all` flag |
| 3.6 | Completed | 2026-05-07 02:33 PM | 2026-05-07 02:37 PM | Add pipeline integration tests — PDF assembly, month name parsing, image path resolution |
| 3.7 | Completed | 2026-05-07 02:37 PM | 2026-05-07 02:39 PM | Run `pytest` (96 pass) and `ruff check && ruff format --check` — all clean |
| 3.8 | Completed | 2026-05-07 02:40 PM | 2026-05-07 02:45 PM | Update `CLAUDE.md` project status and `startup.md` to reflect C4 completion |

### Phase 3 Summary

- **Changes:** Added `OUTPUT_ROOT` to settings, `download_candidate_images()` to image downloader, `render/pipeline.py` orchestrator, `render/__init__.py` export, `render-calendar` CLI subcommand, and integration tests. 96 tests pass, ruff clean.
- **Changes hosted at:** local
- **Commit:** `Implement calendar rendering pipeline with CLI and targeted image download`
