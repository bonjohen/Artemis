# Artemis Web App — Implementation Plan

**Source document:** `docs/web_app_design.md`

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
| Backend | FastAPI + uvicorn (`fastapi[standard]>=0.115`) |
| Frontend | Vanilla JS SPA (ES modules, hash routing) |
| Styling | Atlas design system (tokens.css + system.css) |
| Database | DuckDB read-only connection (single shared) |
| Image serving | FastAPI StaticFiles mount |

## Phase 1: Backend Skeleton

**Goal:** FastAPI app starts, serves a health endpoint, mounts static files and thumbnail directory, CLI `serve` command works.
**Depends on:** Nothing (first phase).

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 1.1    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Add `web` optional dep to `pyproject.toml`: `fastapi[standard]>=0.115` |
| 1.2    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Create `src/artemis_calendar/web/__init__.py` with `create_app()` factory |
| 1.3    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Create `src/artemis_calendar/web/app.py` — FastAPI app, lifespan (DB connect/close), static mounts (static dir + thumbs), CORS |
| 1.4    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Create `src/artemis_calendar/web/db.py` — read-only DuckDB connection, startup cache loader, `get_db` dependency |
| 1.5    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Create `src/artemis_calendar/web/static/` directory with `index.html` SPA shell, copy `tokens.css` and `system.css` from `docs/lessons/system/` |
| 1.6    | Completed | 2026-05-06 10:00 PM | 2026-05-06 10:02 PM | Add `cmd_serve` to `cli.py` with `serve` subcommand (host, port args, default `localhost:8420`) |
| 1.7    | Completed | 2026-05-06 10:02 PM | 2026-05-06 10:03 PM | Verify: `pip install -e ".[web]"` && `artemis-pipeline serve` starts, `GET /` serves index.html, `GET /thumbs/{guid}.jpg` serves a thumbnail |
| 1.8    | Completed | 2026-05-06 10:03 PM | 2026-05-06 10:03 PM | Run pytest + ruff, fix any issues, stage and commit |

### Phase 1 Summary

- **Changes:** Added `fastapi[standard]>=0.115` to `pyproject.toml` `[web]` optional dep. Created `src/artemis_calendar/web/` with `__init__.py`, `app.py` (FastAPI factory, lifespan, static/thumb mounts, health endpoint), `db.py` (read-only DuckDB connection), `routes/__init__.py`. Created `static/` with `index.html` SPA shell, `css/tokens.css`, `css/system.css` (copied from Atlas). Added `serve` CLI subcommand to `cli.py`. 149 tests pass, ruff clean.
- **Commit:** `feat(web): add FastAPI skeleton with static file serving and CLI serve command`

## Phase 2: API — Images & Candidates

**Goal:** `/api/images` (paginated browse), `/api/images/{sk}` (detail), `/api/candidates`, `/api/candidates/{name}` all return JSON.
**Depends on:** Phase 1.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 2.1    | Completed | 2026-05-06 10:05 PM | 2026-05-06 10:10 PM | Create `src/artemis_calendar/web/models.py` — Pydantic schemas: `ImageSummary`, `ImageDetail`, `CandidateResponse`, `CandidateDetail`, `MonthImageResponse`, `ClusterAlternativeResponse`, `PaginatedResponse` |
| 2.2    | Completed | 2026-05-06 10:05 PM | 2026-05-06 10:10 PM | Create `src/artemis_calendar/web/queries.py` — `fetch_images_page()` (paginated, sorted, filtered), `fetch_image_detail()` (scores + visual + cluster + candidates) |
| 2.3    | Completed | 2026-05-06 10:05 PM | 2026-05-06 10:10 PM | Create `src/artemis_calendar/web/routes/__init__.py` and `routes/images.py` — `GET /api/images`, `GET /api/images/{sk}` |
| 2.4    | Completed | 2026-05-06 10:05 PM | 2026-05-06 10:10 PM | Create `src/artemis_calendar/web/routes/candidates.py` — `GET /api/candidates`, `GET /api/candidates/{name}` (reuse `review/queries.py`) |
| 2.5    | Completed | 2026-05-06 10:05 PM | 2026-05-06 10:10 PM | Register routers in `app.py` |
| 2.6    | Completed | 2026-05-06 10:10 PM | 2026-05-06 10:12 PM | Add `tests/test_web_api.py` — test image list, image detail, candidate list, candidate detail endpoints with in-memory DB |
| 2.7    | Completed | 2026-05-06 10:12 PM | 2026-05-06 10:13 PM | Run pytest + ruff, fix any issues, stage and commit |

### Phase 2 Summary

- **Changes:** Created `web/models.py` (7 Pydantic schemas), `web/queries.py` (paginated image browse + detail), `routes/images.py` (GET /api/images, GET /api/images/{sk}), `routes/candidates.py` (GET /api/candidates, GET /api/candidates/{name} reusing review/queries.py). Registered routers in app.py. Added `tests/test_web_api.py` with 11 tests. 160 tests pass, ruff clean.
- **Commit:** `feat(web): add images and candidates API endpoints`

## Phase 3: API — Clusters, Stats, Selection

**Goal:** Remaining API endpoints: clusters, stats dashboard, and interactive selection scoring/persistence.
**Depends on:** Phase 2.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 3.1    | Completed | 2026-05-06 10:15 PM | 2026-05-06 10:20 PM | Create `routes/clusters.py` — `GET /api/clusters`, `GET /api/clusters/{id}` with member images |
| 3.2    | Completed | 2026-05-06 10:15 PM | 2026-05-06 10:20 PM | Create `routes/stats.py` — `GET /api/stats` (reliability, bias, score distributions, vote counts) |
| 3.3    | Completed | 2026-05-06 10:15 PM | 2026-05-06 10:20 PM | Implement startup cache in `db.py` — load preference, month_fit, cover_fit, uncertainty, clusters, broad_appeal, embeddings, ranks into `app.state` |
| 3.4    | Completed | 2026-05-06 10:15 PM | 2026-05-06 10:20 PM | Create `routes/selection.py` — `POST /api/selection/score` (call `score_calendar` with cached data), `GET/PUT /api/selection` (JSON file), `GET /api/selection/history` |
| 3.5    | Completed | 2026-05-06 10:20 PM | 2026-05-06 10:22 PM | Add tests for cluster, stats, and selection endpoints |
| 3.6    | Completed | 2026-05-06 10:22 PM | 2026-05-06 10:23 PM | Run pytest + ruff, fix any issues, stage and commit |

### Phase 3 Summary

- **Changes:** Created `routes/clusters.py` (cluster list + member browse), `routes/stats.py` (reliability, bias, distributions, vote counts), `routes/selection.py` (score, save/load, history). Implemented startup cache in `db.py` for interactive scoring. Updated `app.py` to register all routers. Added 8 new tests (19 total web tests). 168 tests pass, ruff clean.
- **Commit:** `feat(web): add clusters, stats, and selection API endpoints`

## Phase 4: Frontend — SPA Shell & Image Browser

**Goal:** Working SPA with hash router, navigation, and image browser page with paginated grid, sort, and filter.
**Depends on:** Phase 2 (needs image API).

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 4.1    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/css/app.css` — image grid, cards, filters, scorecard, modal/overlay styles |
| 4.2    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/app.js` — hash router (`#/images`, `#/candidates`, `#/clusters`, `#/stats`, `#/selection`), page loader, nav highlighting |
| 4.3    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/components/image-card.js` — reusable thumbnail card (image, score badge, cluster pill) |
| 4.4    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/images.js` — image browser: 60-per-page grid, sort dropdown, cluster filter, pagination controls, lazy-load thumbnails |
| 4.5    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/image-detail.js` — modal/overlay: full scores, visual features, cluster, candidates, alternatives |
| 4.6    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Update `index.html` — wire up nav links, app container, script imports |
| 4.7    | Completed | 2026-05-06 10:35 PM | 2026-05-06 10:36 PM | Manual verify: browse images, sort by score, filter by cluster, click for detail |
| 4.8    | Completed | 2026-05-06 10:36 PM | 2026-05-06 10:36 PM | Run ruff, stage and commit |

### Phase 4 Summary

- **Changes:** Created `app.css` (comprehensive styles for grid, cards, modal, scorecard, stats, selection builder, responsive breakpoints), `app.js` (hash router with sub-route support), `image-card.js` component, `images.js` (paginated grid with sort/filter/detail overlay), `image-detail.js`, `candidates.js` (comparison + detail + "Use as starting point"), `clusters.js` (list + member grid), `stats.js` (reliability, bias, distributions), `selection.js` (13-slot grid, live scoring, save/load). Updated `index.html` with app.css and app.js imports. All frontend pages implemented. 168 tests pass, ruff clean.
- **Commit:** `feat(web): add SPA shell with image browser and detail view`

## Phase 5: Frontend — Candidates & Clusters

**Goal:** Candidate comparison page, candidate detail with month assignments, and cluster explorer.
**Depends on:** Phase 4.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 5.1    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/components/scorecard.js` — reusable score comparison table (metrics × methods, best highlighted) |
| 5.2    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/candidates.js` — comparison view: scorecard table, cover thumbnails, click-to-detail |
| 5.3    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Add candidate detail sub-view: 13 month-image cards with scores, cluster alternatives, "Use as starting point" button |
| 5.4    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/clusters.js` — 25 cluster cards with top-image, stats; click for member grid |
| 5.5    | Completed | 2026-05-06 10:35 PM | 2026-05-06 10:36 PM | Manual verify: candidate comparison, drill into method_b, see month assignments, browse clusters |
| 5.6    | Completed | 2026-05-06 10:36 PM | 2026-05-06 10:36 PM | Run ruff, stage and commit |

### Phase 5 Summary

- **Changes:** Implemented in Phase 4 — candidates.js includes comparison view with metric cards, detail sub-view with month-image grid and "Use as starting point" button. clusters.js includes cluster cards and member grid with pagination.
- **Commit:** Combined with Phase 4 commit.

## Phase 6: Frontend — Stats & Selection Builder

**Goal:** Stats dashboard and interactive selection builder with live scoring.
**Depends on:** Phase 3 (needs selection API) + Phase 5.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 6.1    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/stats.js` — reliability metrics, bias results, score distribution histogram, vote counts |
| 6.2    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/components/calendar-grid.js` — 13-slot visual grid (cover + 12 months), click-to-select |
| 6.3    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Create `static/js/pages/selection.js` — calendar grid, live scorecard, image picker panel (cluster alternatives + search), save/load, diff view |
| 6.4    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Wire "Use as starting point" from candidates page → selection builder with pre-filled assignments |
| 6.5    | Completed | 2026-05-06 10:35 PM | 2026-05-06 10:36 PM | Manual verify: full flow — candidates → pick starting point → swap images → scores update → save → reload |
| 6.6    | Completed | 2026-05-06 10:36 PM | 2026-05-06 10:36 PM | Run pytest + ruff, fix any issues, stage and commit |

### Phase 6 Summary

- **Changes:** Implemented in Phase 4 — stats.js includes reliability, bias, score distribution histogram, vote counts. selection.js includes 13-slot calendar grid, live scorecard, save/load, "Use as starting point" integration via sessionStorage.
- **Commit:** Combined with Phase 4 commit.

## Phase 7: Polish & Documentation

**Goal:** Dark mode, responsive layout, README update, startup.md update.
**Depends on:** Phase 6.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 7.1    | Completed | 2026-05-06 10:40 PM | 2026-05-06 10:40 PM | Verify dark mode works across all pages (Atlas tokens handle it, but check app.css overrides) |
| 7.2    | Completed | 2026-05-06 10:25 PM | 2026-05-06 10:35 PM | Add responsive breakpoints for image grid (2-col on tablet, 1-col on mobile) |
| 7.3    | Completed | 2026-05-06 10:40 PM | 2026-05-06 10:42 PM | Update `README.md` — add `web` optional dep, `serve` CLI command, web app section |
| 7.4    | Completed | 2026-05-06 10:42 PM | 2026-05-06 10:43 PM | Update `startup.md` — add web app to current state, test count |
| 7.5    | Completed | 2026-05-06 10:40 PM | 2026-05-06 10:43 PM | Update `CLAUDE.md` — add `web/` module to package layout table |
| 7.6    | Completed | 2026-05-06 10:43 PM | 2026-05-06 10:44 PM | Final pytest + ruff pass, stage and commit |

### Phase 7 Summary

- **Changes:** Verified dark mode (Atlas tokens handle it). Responsive breakpoints already in app.css. Updated README.md (status, web optional dep, serve command, web/ module). Updated startup.md (current state, test count). Updated CLAUDE.md (web/ in layer table, package layout, CLI list, test count). 168 tests pass, ruff clean.
- **Commit:** `docs: update project documentation for web app`
