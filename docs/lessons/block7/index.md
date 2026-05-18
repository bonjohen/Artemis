# Block 7: Case Study Publication & Web Polish

Lessons from building the public-facing case study site — data curation pages, concurrent database access, and homepage design.

| # | Lesson | Core Teaching |
|---|---|---|
| 058 | [DuckDB Cursor-Per-Request](058_duckdb_cursor_per_request.md) | Shared DuckDB connections break under concurrent web requests; `conn.cursor()` creates thread-safe per-request query contexts |
