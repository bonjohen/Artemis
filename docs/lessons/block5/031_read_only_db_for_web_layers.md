# Lesson 031: Read-Only DB Connections for Web Layers

## The Lesson

When an embedded database (DuckDB, SQLite) serves both a batch pipeline and an interactive web app, the web layer should open the database in read-only mode. This avoids writer-lock conflicts entirely and makes the architecture self-documenting: the web app *cannot* mutate the warehouse, by construction.

## Context

A calendar image selection platform uses DuckDB as its single-file analytical warehouse. The batch pipeline (CLI) writes scores, clusters, and calendar candidates. A new FastAPI web app needed to browse 12,217 images, compare 5 calendar candidates, and score custom selections — all read operations against the same warehouse file. DuckDB enforces an exclusive write lock: only one process can hold a write connection at a time (see lesson 002). If the web app opened a normal read-write connection, running any pipeline command while the web server was up would fail with a file-lock error.

## What Happened

1. The existing pipeline already serialized writes: each CLI command opens a connection, writes, and closes before the next command runs. This worked because pipeline steps are sequential.
2. The web app, by contrast, holds a connection for its entire lifetime (server start to shutdown). A read-write connection would lock out the pipeline for as long as the server ran.
3. Used `duckdb.connect(path, read_only=True)` in the web app's startup lifespan. DuckDB allows multiple concurrent read-only connections alongside a single writer — or multiple readers with no writer.
4. This made the web app and pipeline CLI fully independent. The server can run continuously while the user re-runs scoring or optimization from the CLI. The web app sees the updated data on the next query.
5. Interactive selection state (custom calendar assignments) was stored as JSON files on disk rather than in the warehouse, keeping the web app truly read-only with zero write-path complications.

## Key Insights

- **Read-only is an architectural constraint, not just an optimization.** Opening in `read_only=True` doesn't just avoid locks — it guarantees the web layer can never corrupt or modify the warehouse. This removes an entire class of bugs and makes the data flow unidirectional: pipeline writes, web reads.

- **Embedded databases make the lock model visible.** With PostgreSQL, concurrent connections "just work" because a server process mediates. With DuckDB or SQLite, the application is the database server, so lock management is the application's problem. Making the web layer read-only is the simplest solution.

- **Side-channel writes avoid the constraint entirely.** The selection builder needed to save user choices. Writing JSON files to disk (`output/selections/`) kept the web app read-only while still providing persistence. This is simpler and more debuggable than a secondary write-enabled DB connection.

- **Hot reload comes free.** Since the web app re-queries on each request, running `artemis-pipeline optimize` in a terminal updates the warehouse, and the next page load shows the new data. No restart, no cache invalidation.

## Applicability

This pattern applies whenever an embedded database serves both a batch writer and an interactive reader. It does NOT apply to client-server databases (PostgreSQL, MySQL) where concurrent read-write connections are the normal operating mode. It also doesn't help if the web app genuinely needs to write to the database — in that case, you need either a connection pool with serialized writes or a switch to a client-server DB.

## Related Lessons

- [DuckDB Single-Writer Constraint](../block1/duckdb_single_writer_constraint.md) — the underlying constraint that drives this pattern; that lesson covers the pipeline side, this one covers the web side
- [Startup Cache for Interactive Scoring](032_startup_cache_for_interactive_scoring.md) — the companion pattern: cache scoring data in memory so per-request DB queries are only needed for browse/search, not for the hot scoring path
