# Artemis Web App — Design Document

## 1. Purpose

Replace static PDF review packages with an interactive web app for browsing 12,217 images, comparing 5 calendar candidates, exploring clusters/stats, and manually assembling a custom calendar with live score feedback. Single-user, local-only (localhost).

## 2. Technology Choices

| Concern | Choice | Why |
|---|---|---|
| Backend | FastAPI + uvicorn | One dep (`fastapi[standard]`), async, auto OpenAPI docs, Pydantic models map to existing dataclasses |
| Frontend | Vanilla JS SPA (ES modules, no build step) | Proven by lessons viewer. Hash routing. No npm/webpack. |
| Styling | Atlas design system (tokens.css + system.css) | Visual consistency with lessons viewer. Dark mode free. |
| Database | DuckDB read-only connection | Single `duckdb.connect(read_only=True)` at startup, reused across requests. Avoids writer lock conflict with pipeline. |
| Image serving | FastAPI StaticFiles mount | `D:/artemis/raw/images/thumbs/` mounted at `/thumbs/`. Browser loads `<img src="/thumbs/{guid}.jpg">` directly. |
| Custom selection state | JSON files | `D:/artemis/output/selections/{name}.json`. Human-readable, diffable, no warehouse pollution. |
| New dependency | `fastapi[standard]>=0.115` added to `[project.optional-dependencies] web` | Bundles uvicorn, keeps core deps clean. |

## 3. Package Layout

```
src/artemis_calendar/web/
    __init__.py          # create_app() factory
    app.py               # FastAPI app, lifespan, static mounts, router includes
    db.py                # read-only connection, startup cache loader, DI dependency
    models.py            # Pydantic response schemas
    queries.py           # new queries (image browse, cluster browse, stats)
    routes/
        __init__.py
        images.py        # GET /api/images, GET /api/images/{sk}
        candidates.py    # GET /api/candidates, GET /api/candidates/{name}
        clusters.py      # GET /api/clusters, GET /api/clusters/{id}
        stats.py         # GET /api/stats
        selection.py     # GET/PUT /api/selection, POST /api/selection/score
    static/
        index.html       # SPA shell (nav, container div, script imports)
        css/
            tokens.css   # symlinked or copied from docs/lessons/system/
            system.css   # symlinked or copied from docs/lessons/system/
            app.css      # app-specific styles (image grid, scorecard, etc.)
        js/
            app.js       # hash router, page loader
            pages/
                images.js      # image browser grid
                image-detail.js
                candidates.js  # candidate comparison + detail
                clusters.js    # cluster explorer
                stats.js       # stats dashboard
                selection.js   # custom calendar builder
            components/
                image-card.js  # reusable thumbnail card
                scorecard.js   # score comparison table
                calendar-grid.js  # 13-slot visual grid
```

CLI entry point: `artemis-pipeline serve` → starts uvicorn on `localhost:8420`.

## 4. API Endpoints

### Images
| Endpoint | Params | Returns |
|---|---|---|
| `GET /api/images` | `page`, `per_page` (default 60), `sort` (score, cluster, brightness), `cluster_id`, `min_score` | Paginated list: `{items: [...], total, page, pages}` |
| `GET /api/images/{sk}` | — | Full detail: scores, visual features, cluster, candidates containing this image, cluster alternatives |

### Candidates
| Endpoint | Returns |
|---|---|
| `GET /api/candidates` | All 5 candidates with calendar-level scores (reuses `fetch_all_candidates`) |
| `GET /api/candidates/{name}` | 13 month-image assignments with all scores, visual features, alternatives (reuses `fetch_candidate_images` + `fetch_cluster_alternatives`) |

### Clusters
| Endpoint | Returns |
|---|---|
| `GET /api/clusters` | All cluster summaries with stats, top image GUID for thumbnail |
| `GET /api/clusters/{id}` | Member images (paginated), cluster stats |

### Stats
| Endpoint | Returns |
|---|---|
| `GET /api/stats` | Reliability metrics, bias detection results, score distributions (histogram buckets), vote mode breakdown |

### Selection (custom calendar builder)
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/selection` | GET | Load current custom selection |
| `/api/selection` | PUT | Save selection (writes JSON to disk) |
| `/api/selection/score` | POST | Score a proposed 13-image assignment using `optimize/scoring.py:score_calendar`. Body: `{assignments: [{image_sk, sequence_number}, ...]}` |
| `/api/selection/history` | GET | List saved selections |

## 5. Data Flow for Interactive Selection

The key interactive feature: user modifies a calendar and sees scores update live.

1. User starts from a candidate (e.g., method_b) → loads its 13 assignments
2. User clicks a month slot → sees cluster alternatives + full image browser
3. User picks a replacement image → JS updates local `assignments[]` array
4. JS POSTs to `/api/selection/score` with the 13-assignment array
5. Server loads scoring inputs from cached dicts (preference, month_fit, cover_fit, uncertainty, clusters, embeddings — all cached in `app.state` at startup, total <5MB)
6. Server calls `score_calendar()` → returns component scores in <50ms
7. JS re-renders the scorecard with new scores, highlights changes from baseline

## 6. Startup Cache

At app startup, load into `app.state`:
- `preference: dict[int, float]` — posterior_mean for all 12,217 images
- `month_fit: dict[int, ndarray]` — month-fit vectors (13-dim per image)
- `cover_fit: dict[int, float]` — cover suitability scores
- `uncertainty: dict[int, float]` — uncertainty scores
- `clusters: dict[int, int]` — visual cluster assignments
- `broad_appeal: dict[int, float]` — broad appeal scores
- `embeddings: dict[int, ndarray]` — CLIP 512-dim vectors (optional, ~24MB — could defer)
- `ranks: dict[int, int]` — preference ranks

This eliminates per-request DB queries during interactive scoring. Total memory: <30MB including embeddings.

## 7. Reuse from Existing Code

| Existing | Reuse in web |
|---|---|
| `review/queries.py` — `fetch_all_candidates`, `fetch_candidate_images`, `fetch_cluster_alternatives`, `fetch_all_preference_ranks`, `resolve_run_id` | Direct import in candidate routes |
| `review/queries.py` — `CandidateScore`, `MonthImage`, `ClusterAlternative` dataclasses | Convert to Pydantic models in `web/models.py` |
| `optimize/scoring.py` — `score_calendar()` | Called by `/api/selection/score` endpoint |
| `optimize/month_fit.py` — month-fit scoring functions | Used to populate startup cache |
| `config/settings.py` — `DB_PATH`, `RAW_ROOT`, `OUTPUT_ROOT` | Path configuration |
| `config/database.py` — `apply_migrations` | Ensure schema exists at startup |
| `docs/lessons/system/tokens.css`, `system.css` | Static file serving for frontend |

## 8. Frontend Pages

### Image Browser (`#/images`)
- 60-thumbnail grid, lazy-loaded
- Sort dropdown: Score (default), Brightness, Cluster
- Filter pills: cluster ID, min score slider
- Click → image detail overlay

### Candidate Comparison (`#/candidates`)
- Score matrix table (7 metrics × 5 methods), best highlighted
- Cover thumbnail per candidate
- Click candidate → detail view with 13 month-image cards
- Each card shows: thumbnail, month label, scores, cluster ID
- "Use as starting point" button → copies to selection builder

### Cluster Explorer (`#/clusters`)
- 25 cluster cards with top-image thumbnail, member count, mean score
- Click → cluster detail with member image grid

### Stats Dashboard (`#/stats`)
- Reliability: Krippendorff's alpha per vote mode
- Bias: position bias coefficient/p-value, cluster bias chi2
- Score distributions: posterior_mean histogram, Elo histogram
- Vote counts: batch ballots, pairwise votes, category rankings

### Selection Builder (`#/selection`)
- 13-slot grid (cover + 12 months), each showing current image thumbnail
- Live scorecard (objective, popularity, diversity, month-fit, redundancy, uncertainty)
- Click slot → picker panel with: cluster alternatives, top-scoring unselected images, search
- Swap image → instant score recalculation via API
- Save/load buttons, selection name input
- Diff view: show score delta vs. baseline candidate

## 9. Verification

After implementation:
1. `pip install -e ".[web]"` — installs FastAPI
2. `artemis-pipeline serve` — starts on localhost:8420
3. Browser opens to image grid with 12,217 thumbnails loading
4. Navigate to candidates → see 5-method comparison
5. Click into method_b → see 13 month assignments
6. Click "Use as starting point" → selection builder pre-filled
7. Swap one image → scores recalculate and display
8. Save selection → JSON file appears in output/selections/
9. Stats page shows reliability and bias metrics
10. pytest + ruff clean
