# PEP 8 Compliance — Implementation Plan

**Source document:** `docs/pep8_review_pdr.md`

## Work Queue Instructions

### State Transitions

Open  -->  Started  -->  Completed
              |
              └-->  Blocked  -->  Started  -->  Completed

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
| Linter | `ruff check` (rules: E, F, W, I, N, UP, B, SIM) |
| Formatter | `ruff format` (line-length 120) |
| Test runner | `pytest` |

## Phase 1: Format and Fix All Violations

**Goal:** Zero `ruff check` violations and zero `ruff format` drift across `src/` and `tests/`.
**Depends on:** Nothing (first phase).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-10 12:25 AM (PST) | 2026-05-10 12:25 AM (PST) | Run `ruff format src/ tests/` — fixes 25 files of whitespace/wrapping drift |
| 1.2 | Completed | 2026-05-10 12:25 AM (PST) | 2026-05-10 12:25 AM (PST) | Run `ruff check --fix src/artemis_calendar/web/app.py` — auto-sort imports (I001) |
| 1.3 | Completed | 2026-05-10 12:25 AM (PST) | 2026-05-10 12:26 AM (PST) | Add `strict=True` to 5 `zip()` calls: `features/dedup.py:172`, `vision/clip_tagger.py:173,175,386,388` |
| 1.4 | Completed | 2026-05-10 12:26 AM (PST) | 2026-05-10 12:27 AM (PST) | Add `per-file-ignores` to `pyproject.toml`: `"src/artemis_calendar/web/routes/*.py" = ["B008"]` for idiomatic FastAPI `Depends()` |
| 1.5 | Completed | 2026-05-10 12:27 AM (PST) | 2026-05-10 12:28 AM (PST) | Verify: `ruff check src/ tests/` reports 0 violations |
| 1.6 | Completed | 2026-05-10 12:28 AM (PST) | 2026-05-10 12:28 AM (PST) | Verify: `ruff format --check src/ tests/` reports 0 files would be reformatted |
| 1.7 | Completed | 2026-05-10 12:28 AM (PST) | 2026-05-10 12:38 AM (PST) | Run `pytest` — 245 passed, 14 pre-existing failures (MockTagger hash overflow + missing dedup table in test DB, confirmed on clean main) |
| 1.8 | Completed | 2026-05-10 12:38 AM (PST) | 2026-05-10 12:38 AM (PST) | Stage and commit: `style: apply ruff format, fix zip strict, sort imports, suppress B008` |

### Phase 1 Summary

- **Changes:** Reformatted 25 files via `ruff format`, auto-sorted imports in `web/app.py`, added `strict=True` to 5 `zip()` calls in `features/dedup.py` and `vision/clip_tagger.py`, added `per-file-ignores` for B008 (FastAPI `Depends()`) in `pyproject.toml`. Zero ruff check violations, zero format drift. 245 tests pass (14 pre-existing failures unrelated to this change).
- **Changes hosted at:** TBD
- **Commit:** `style: apply ruff format, fix zip strict, sort imports, suppress B008`

## Phase 2: Verify and Document

**Goal:** Confirm clean state persists and update project documentation.
**Depends on:** Phase 1.

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-10 12:49 AM (PST) | 2026-05-10 12:49 AM (PST) | Verify web server starts cleanly: `curl -s http://localhost:8070/api/health` |
| 2.2 | Completed | 2026-05-10 12:49 AM (PST) | 2026-05-10 12:51 AM (PST) | Update lesson count in `docs/lessons/lessons.html` hero stats: 58 → 57 (matches actual card count) |
| 2.3 | Completed | 2026-05-10 12:51 AM (PST) | 2026-05-10 12:52 AM (PST) | Stage and commit: `docs: verify PEP 8 compliance, fix lesson count in hero stats` |

### Phase 2 Summary

- **Changes:** Verified web server starts cleanly (`/api/health` → ok). Corrected lesson count in `docs/lessons/lessons.html` hero stats from 58 to 57 (matching actual card count).
- **Changes hosted at:** TBD
- **Commit:** `docs: verify PEP 8 compliance, fix lesson count in hero stats`
