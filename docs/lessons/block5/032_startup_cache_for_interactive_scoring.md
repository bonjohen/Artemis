# Lesson 032: Startup Cache for Interactive Scoring

## The Lesson

When an interactive web app needs sub-100ms responses from a scoring function that depends on large lookup tables, load those tables into memory at startup rather than querying the database per request. The cache size is bounded (you know exactly what's in the warehouse), startup cost is a one-time hit, and the scoring path becomes a pure function over in-memory dicts.

## Context

A calendar selection web app lets users swap images in a 13-slot calendar and see updated scores instantly. The scoring function (`score_calendar`) computes a weighted objective from seven components: preference, diversity, month-fit, cover-fit, redundancy (max pairwise CLIP cosine similarity), uncertainty, and broad appeal. Each component requires a lookup dict keyed by image_sk — preference scores for 12,217 images, cluster assignments for 12,217 images, CLIP embeddings (512-dim float32 vectors) for 12,217 images, and smaller dicts for cover-fit and uncertainty. The database is DuckDB opened in read-only mode, so queries are fast — but "fast" for analytics (10-50ms) is not fast enough for the interactive scoring loop where the user expects instant feedback on each swap.

## What Happened

1. Initially planned to query the database on each `/api/selection/score` POST. Estimated ~200ms per request for the 5 SQL queries needed to assemble the scoring inputs.
2. Calculated the memory footprint of caching everything: 12,217 floats for preference (~100KB), 12,217 ints for clusters (~50KB), 12,217 CLIP vectors at 512 × 4 bytes each (~24MB). Total under 30MB — negligible for a single-user local app.
3. Implemented `_load_cache()` in the FastAPI lifespan startup. Six queries load all scoring dicts into `app.state`. The queries run once at server start, taking ~1 second total.
4. The `/api/selection/score` endpoint reads cached dicts from `request.app.state` and calls `score_calendar()` — a pure Python function with no DB access. Response time dropped from ~200ms to <10ms.
5. Browse and search endpoints (`/api/images`, `/api/clusters`) still query the database per request, because their results are paginated, filtered, and sorted — caching all possible query results would be impractical and unnecessary at pagination-friendly latencies.

## Key Insights

- **Cache the hot path, query the cold path.** Interactive scoring is the hot path — it's called on every user interaction and needs to feel instant. Image browsing is the cold path — users tolerate 50-100ms page loads, and the query space (sort × filter × page) is too large to cache. Identifying which path is which determines the caching strategy.

- **Bounded data makes caching simple.** The warehouse has exactly 12,217 scored images. This number doesn't grow during a web session. There's no cache invalidation problem because the data only changes when the pipeline reruns, and the user can just restart the server. Unbounded or streaming data would need a different approach.

- **`app.state` is FastAPI's natural cache location.** FastAPI's `app.state` is a simple namespace that lives for the app's lifetime. No external cache (Redis, memcached) needed. The lifespan context manager provides clean startup/shutdown hooks. This is the right level of complexity for a single-user local app.

- **Scoring functions should be pure.** `score_calendar()` takes dicts as arguments — it doesn't reach into a database or global state. This made caching trivial: pre-load the dicts, pass them in. If the function had embedded SQL queries, caching would have required either mocking the DB or rewriting the function.

- **24MB of CLIP embeddings is the heaviest item.** The embeddings enable redundancy scoring (max pairwise cosine similarity). Without them, scoring is ~100KB of cached data. With them, it's ~24MB. The trade-off is worth it for a local app, but for a multi-tenant server you'd want to defer embedding loading or compute redundancy differently.

## Examples

```python
# Startup: load once
def _load_cache(app):
    conn = app.state.db
    rows = conn.execute("SELECT image_sk, posterior_mean FROM mart_image_preference_score WHERE ...").fetchall()
    app.state.preference = {int(r[0]): float(r[1] or 0) for r in rows}
    # ... repeat for clusters, embeddings, cover_fit, uncertainty

# Hot path: pure function, no DB
@router.post("/api/selection/score")
def score_selection(body: ScoreRequest, request: Request):
    return score_calendar(
        selected_sks=[a.image_sk for a in body.assignments],
        preference=request.app.state.preference,  # cached dict
        embeddings=request.app.state.embeddings,   # cached dict
        ...
    )

# Cold path: query DB per request (paginated, filtered)
@router.get("/api/images")
def list_images(page, sort, cluster_id, conn=Depends(get_db)):
    return fetch_images_page(conn, page, ...)  # SQL query
```

## Applicability

This pattern works when: (1) the dataset is bounded and fits in memory, (2) the scoring function is a pure function of lookup data, and (3) the data changes infrequently (batch pipeline, not streaming). It does NOT work for: multi-tenant apps where each tenant has different data, streaming systems where scores change continuously, or datasets too large to fit in memory.

## Related Lessons

- [Read-Only DB for Web Layers](031_read_only_db_for_web_layers.md) — the web app opens the DB read-only, making the cache the primary data source for scoring
- [Per-Record Overhead at Scale](../block1/per_record_overhead_at_scale.md) — the general principle that small per-item costs multiply dangerously; here, per-request DB round-trips are the overhead
