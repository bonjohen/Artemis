# Lesson 063: Promise.all as an Accidental Concurrency Test

## The Lesson

Any frontend page that fires multiple `fetch()` calls via `Promise.all()` is an implicit concurrency test for the backend. If your API endpoints work individually via `curl` but fail when the browser loads a page that hits them simultaneously, you have a shared-state concurrency bug — not a data or query problem.

## Context

A FastAPI web app served data from a DuckDB database through multiple API endpoints. Each endpoint was tested individually during development using `curl` and all returned correct JSON. The app had been running for weeks with no issues. Then a new page was added that needed data from three endpoints simultaneously — dedup summary, group size distribution, and dark frame statistics — fetched in parallel via `Promise.all()`.

## What Happened

1. The new curation page was built with three parallel API fetches:
   ```javascript
   const [summary, distribution, darkStats] = await Promise.all([
     fetch('/api/dedup/summary').then(r => r.json()),
     fetch('/api/dedup/distribution').then(r => r.json()),
     fetch('/api/dedup/dark-stats').then(r => r.json()),
   ]);
   ```

2. The page loaded with all zeros. Browser console showed `500 Internal Server Error` on one or more of the three requests. The specific endpoint that failed was non-deterministic — sometimes summary, sometimes dark-stats.

3. Testing each endpoint individually with `curl` returned correct data every time. The bug only appeared when the browser fired all three requests at once.

4. Server logs revealed the pattern: two requests succeeded, the third threw an unhandled exception in uvicorn's ASGI handler. The root cause was a single shared DuckDB connection being used by all request handlers — DuckDB's Python driver doesn't support concurrent queries on the same connection object.

5. Previous pages had never exposed this bug because they each made only one API call, or made sequential calls (await one, then fetch another). The curation page was the first to fire 3+ concurrent requests.

6. The fix was a one-line change: return `conn.cursor()` per request instead of the shared connection. But the diagnostic insight — "works in curl, fails in browser" equals concurrency bug — was the real lesson.

## Key Insights

- **`Promise.all()` is the cheapest concurrency test you'll ever write.** You don't need a load testing tool to find concurrency bugs. Any SPA page that fetches from multiple endpoints simultaneously will expose shared-state issues in the backend. If your page needs 3 pieces of data, fetch them in parallel — you'll find bugs faster than sequential fetches would.

- **"Works in curl, fails in browser" is a diagnostic pattern.** When an endpoint works when tested alone but fails in the real application, the first hypothesis should be concurrency, not data. Sequential tools (curl, Postman, unit tests) cannot reproduce timing-dependent bugs that only manifest under parallel access.

- **The non-deterministic endpoint failure is the signature.** If the *same* endpoint fails every time, it's a query or data bug. If *different* endpoints fail on different page loads, the problem is shared state being corrupted by interleaved access. The randomness is the clue.

- **Thread-pool web servers turn every concurrent request into a thread-safety test.** FastAPI with uvicorn dispatches synchronous handlers to a thread pool. Three browser requests become three threads hitting the same Python objects. Any object shared across handlers — database connections, caches, counters — must be thread-safe or per-request.

- **Add a multi-fetch page early in development.** If the curation page had been built earlier, the concurrency bug would have been caught earlier. Consider adding a health-check or dashboard page that hits multiple endpoints in parallel as an intentional integration test.

## Examples

Sequential fetch (hides concurrency bugs):
```javascript
const summary = await fetch('/api/summary').then(r => r.json());
const distribution = await fetch('/api/distribution').then(r => r.json());
const darkStats = await fetch('/api/dark-stats').then(r => r.json());
```

Parallel fetch (exposes concurrency bugs):
```javascript
const [summary, distribution, darkStats] = await Promise.all([
  fetch('/api/summary').then(r => r.json()),
  fetch('/api/distribution').then(r => r.json()),
  fetch('/api/dark-stats').then(r => r.json()),
]);
```

Both patterns are functionally equivalent for the page, but the parallel version is faster *and* acts as a concurrency smoke test.

## Applicability

This applies to any web application with a multi-threaded or async backend (FastAPI, Flask with gunicorn, Express, etc.) that serves data from a stateful resource (database, cache, file handle). It does NOT apply to stateless backends where each request creates its own resources from scratch, or to backends that use connection pools with proper per-request checkout.

## Related Lessons

- [DuckDB Cursor-Per-Request](058_duckdb_cursor_per_request.md) — the specific fix for the concurrency bug this lesson describes

## Metadata

- **Category:** eng
- **Block:** block7
- **Tags:** concurrency, testing, frontend, promise-all, debugging
