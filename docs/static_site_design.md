# Static Site Design Document

## 1. Purpose

Host the Artemis Calendar web app as a set of static pages on GitHub Pages, following the patterns established in `bonjohen/certification` (pure static, JSON data files) and `bonjohen/jobclass` (build script + fetch shim).

## 2. Scope

Convert the existing FastAPI SPA into a statically hostable site with pre-generated API responses. All read-only functionality preserved. Interactive selection builder becomes read-only (no server-side scoring or file writes on static hosting).

## 3. Approach: JobClass Fetch Shim Pattern

The JobClass project uses a build script that:
1. Starts the FastAPI app via `TestClient`
2. Hits every API endpoint and saves responses as JSON files
3. Copies static assets (HTML, CSS, JS)
4. Injects a **fetch shim** into `index.html` that intercepts `fetch()` calls and redirects them to static JSON files
5. Deploys `_site/` to GitHub Pages via `peaceiris/actions-gh-pages`

This approach requires **zero changes to existing frontend JS** — the shim transparently serves pre-generated data.

## 4. Key Design Decisions

### Thumbnails: R2 CDN, not local files
12,217 thumbnails at ~20KB each = ~244MB. Too heavy for a git repo. The thumbnails already live on the R2 CDN at `https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/{guid}.jpg`. The build script rewrites `/thumbs/` references to the CDN URL.

### API data: Pre-generate all responses as JSON
- `/api/images` — Single `all.json` with all 12,217 image summaries (~1.2MB). Shim handles sort/filter/pagination client-side.
- `/api/images/{sk}` — Single `details.json` keyed by image_sk (~2.4MB). Shim extracts entry on demand.
- `/api/candidates` — `index.json` + per-candidate `{name}.json` (5 files)
- `/api/clusters` — `index.json` + per-cluster `{id}.json` (25 files)
- `/api/stats` — Single `stats.json`
- `/api/selection` — Read returns empty default; write disabled in static mode
- `/api/health` — Static `{"status": "ok"}`

### Selection builder: Read-only in static mode
The selection builder requires server-side scoring (CLIP embeddings, composite objective function). This cannot run in the browser. In static mode, the score button shows a message that scoring requires the local server.

## 5. Output Structure

```
_site/
  index.html              (fetch shim injected)
  .nojekyll
  static/
    css/                   (tokens.css, system.css, app.css)
    js/                    (app.js, pages/*, components/* — thumb URLs rewritten)
  api/
    health.json
    stats.json
    images/
      all.json             (12,217 summaries for browse/filter)
      details.json         (12,217 detail records keyed by sk)
    candidates/
      index.json
      method_a.json ... method_e.json
    clusters/
      index.json
      0.json ... 24.json
```

## 6. GitHub Actions Deployment

```yaml
on: push to main
jobs:
  deploy:
    - checkout
    - setup python
    - pip install .[web]
    - download warehouse.duckdb from release artifact
    - python scripts/build_static.py
    - deploy _site/ via peaceiris/actions-gh-pages
```
