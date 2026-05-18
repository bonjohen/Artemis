# Block 7: Case Study Publication & Web Polish

7 lessons from building the public-facing case study site — data curation pages, concurrent database access, homepage design, and portfolio presentation patterns.

| # | Lesson | Core Teaching |
|---|---|---|
| 058 | [DuckDB Cursor-Per-Request](058_duckdb_cursor_per_request.md) | Shared DuckDB connections break under concurrent web requests; `conn.cursor()` creates thread-safe per-request query contexts |
| 059 | [Derived Metrics from Immutable Tables](059_derived_metrics_from_immutable_tables.md) | Derive dashboard metrics from immutable fact tables, not mutable state flags that can be toggled |
| 060 | [Context Blocks for Case Study Narration](060_context_blocks_for_case_study_narration.md) | A one-sentence "why this page matters" block turns a data app into a self-guided case study |
| 061 | [Centralized Metadata Constants](061_centralized_metadata_constants.md) | Centralize project counts in a config module + live API fetch to prevent silent count drift |
| 062 | [Five-Minute Reviewer Path](062_five_minute_reviewer_path.md) | A numbered guided walkthrough ensures portfolio reviewers see the strongest work first |
| 063 | [Promise.all as Concurrency Test](063_promise_all_as_concurrency_test.md) | Parallel browser fetches expose shared-state concurrency bugs that sequential curl testing misses |
| 064 | [Noscript Fallback for SPA SEO](064_noscript_fallback_for_spa_seo.md) | Meta tags + noscript block provide crawlable baseline for JS-rendered single-page apps |
