# Lesson 058: DuckDB Cursor-Per-Request for Concurrent Web Handlers

## The Lesson

When serving DuckDB through a multi-threaded web framework (FastAPI/uvicorn), never share a single connection object across concurrent request handlers. Instead, call `conn.cursor()` to create a per-request cursor. DuckDB's Python driver does not support concurrent queries on the same connection from multiple threads, but multiple cursors on a single read-only connection execute safely in parallel.

## Context

The Artemis web app uses a single read-only DuckDB connection opened at startup (`duckdb.connect(path, read_only=True)`) and injected into FastAPI route handlers via `Depends(get_db)`. This pattern worked for months because most pages make one API call at a time. When the Data Curation page was added, it fired three `fetch()` calls via `Promise.all()` — hitting `/api/dedup/summary`, `/api/dedup/distribution`, and `/api/dedup/dark-stats` simultaneously.

## What Happened

1. The curation page loaded with all zeros in the stats bar. Browser console showed `500 Internal Server Error` on one or more of the three endpoints.

2. Server logs confirmed: the first two requests succeeded, but the third threw an unhandled exception inside uvicorn's ASGI handler. The traceback pointed to DuckDB's internal state being corrupted by concurrent access.

3. The root cause: uvicorn dispatches synchronous route handlers to a thread pool. Three concurrent requests meant three threads calling `conn.execute()` on the same `DuckDBPyConnection` object simultaneously. DuckDB's Python binding uses an internal cursor per connection, and concurrent `execute()` calls interleave their state.

4. The fix was a one-line change in `web/db.py`:

```python
# Before — shared connection, breaks under concurrency
def get_db(request: Request) -> duckdb.DuckDBPyConnection:
    return request.app.state.db

# After — per-request cursor, safe for concurrent reads
def get_db(request: Request) -> duckdb.DuckDBPyConnection:
    return request.app.state.db.cursor()
```

5. After the fix, all three endpoints responded successfully in parallel. The `cursor()` method creates a lightweight cursor that shares the underlying connection's read-only access but maintains its own query state.

## Key Insights

- **DuckDB connections are not thread-safe; cursors are.** A single `DuckDBPyConnection` tracks one active query at a time. Calling `cursor()` creates an independent query context that can execute in parallel with other cursors on the same connection. This is documented but easy to miss when the single-connection pattern works fine for sequential requests.
- **The bug only manifests under concurrency.** Serial `curl` requests work perfectly. The bug surfaces only when a browser fires parallel fetches — which is exactly what `Promise.all()` does. This makes it invisible during endpoint-by-endpoint testing and only appears in integration testing or real browser use.
- **Read-only connections are the right base.** Opening the connection with `read_only=True` at startup means cursors cannot accidentally write. The cursor-per-request pattern adds no meaningful overhead — cursor creation is near-instant and cursors are garbage-collected after the request completes.
- **Watch for "works in curl, fails in browser" as a concurrency signal.** When an endpoint works individually but fails when a page loads (which hits multiple endpoints), the first hypothesis should be a shared-state concurrency issue, not a data or query problem.

## Metadata

- **Category:** eng
- **Block:** block7
- **Tags:** duckdb, concurrency, fastapi, web, cursor
