# Lesson 037: Static Site Generation via Fetch Shim

## The Lesson

A FastAPI + JavaScript SPA can be deployed to GitHub Pages without rewriting frontend code by using a **fetch shim** — a small JavaScript interceptor injected into `index.html` that redirects API calls to pre-generated JSON files and handles filtering, sorting, and pagination client-side. The build script exports all API data during a one-time build step, and the existing frontend JavaScript works unchanged.

## Context

The Artemis Calendar web app is a vanilla JS SPA backed by a FastAPI server that queries a DuckDB warehouse. The app has 5 API-consuming pages (image browser with sort/filter/pagination, candidate comparison, cluster explorer, stats dashboard, interactive selection builder). Hosting on GitHub Pages requires eliminating the Python backend while preserving the interactive browsing experience for 12,217 images.

## What Happened

1. Evaluated two reference projects: `certification` (pure static JSON, no build step) and `jobclass` (build script + fetch shim). The certification pattern doesn't apply because Artemis has dynamic filtering and pagination. The jobclass pattern does.

2. Wrote `scripts/build_static.py` that:
   - Starts the FastAPI app via Starlette's `TestClient` (requires using it as a context manager to trigger the lifespan and `init_db`)
   - Hits every API endpoint and saves responses as JSON files
   - Bundles all 12,217 image summaries into one `all.json` (~1.2 MB) for client-side filtering
   - Bundles all image details into one `details.json` keyed by `image_sk` (~7 MB)
   - Pre-generates per-candidate and per-cluster JSON files
   - Injects a fetch shim into `index.html` before `</head>`
   - Rewrites thumbnail URLs from `/thumbs/` to the R2 CDN

3. The fetch shim intercepts `window.fetch`, checks if the URL matches `/api/`, and either:
   - Loads a cached JSON file and applies client-side logic (filter, sort, paginate)
   - Returns a synthetic `Response` object for disabled endpoints (selection save, scoring)
   - Falls through to the original `fetch` for non-API requests (CSS, JS, images)

4. Key decisions:
   - **Thumbnails on CDN**: 12,217 thumbnails at ~20 KB each = 244 MB. Too large for a git repo. They already exist on the R2 CDN, so the build script rewrites all `/thumbs/` references to the CDN URL.
   - **Selection builder read-only**: Interactive scoring requires CLIP embeddings in memory (~50 MB). The shim returns a 501 for score/save endpoints with a message directing users to the local server.
   - **Single-file detail bundle**: Instead of 12,217 individual JSON files, all details go into one `details.json` that the shim loads lazily and caches. This reduces file count and avoids GitHub Pages rate limits on many small file fetches.

## Alternatives Considered

- **Rewrite frontend to use static JSON directly**: Would require changing every `fetch()` call in every page module. The shim approach requires zero frontend changes.
- **Pre-generate all pagination combinations**: With 3 sort orders and 25 cluster filters, combinatorial explosion makes this impractical. Client-side filtering on the full dataset is fast enough (12K records, ~1.2 MB).
- **Use a service worker instead of a fetch shim**: More complex, harder to debug, and unnecessary when the shim is a simple synchronous script injection.

## Key Takeaway

The fetch shim pattern turns any API-backed SPA into a static site without touching frontend code. The tradeoff is a build step that runs against the database, and client-side data that must fit in memory. For datasets under ~50K records, this is a practical and maintainable approach.

## Related Lessons

- [Lesson 043: PII Sanitization in Static Exports](../block6/043_pii_sanitization_in_static_exports.md) — the static site consumes JSON files produced by the exporter; PII sanitization ensures these files are safe for public serving
