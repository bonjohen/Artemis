# Lesson: DuckDB Single-Writer Constraint in Concurrent Pipelines

## Problem

While developing the concurrent thumbnail downloader, the DuckDB warehouse file (`warehouse.duckdb`) became locked by the download process. Any attempt to check progress, run `artemis-pipeline status`, or open a second connection failed with:

```
IO Error: Cannot open file "D:\artemis\warehouse.duckdb":
The process cannot access the file because it is being used by another process.
```

The pipeline appeared hung from the outside, but was actually working fine — just unreachable for monitoring.

## Why It Matters

DuckDB is an embedded analytical database optimized for single-process use. Unlike PostgreSQL or MySQL, it doesn't have a server process that manages connections. The database file is opened directly by the application process, and DuckDB uses an exclusive write lock. This is a fundamental architectural property, not a bug.

This constraint shapes how you design concurrent pipelines that use DuckDB as their warehouse.

## The Constraint in Detail

- **One writer at a time.** Only one process can hold a write connection to a DuckDB file. A second `duckdb.connect()` call from another process will block or fail.
- **Multiple readers are fine** if you open in read-only mode: `duckdb.connect(path, read_only=True)`. But the writer lock must not be held.
- **Within a single process**, a single `DuckDBPyConnection` is not thread-safe for concurrent writes. However, you can use `conn.cursor()` to create cursors for concurrent reads.
- **The lock is held for the lifetime of the connection**, not per-transaction. Closing the connection releases the lock.

## How We Worked Around It

### Pattern 1: Separate I/O from DB writes

The concurrent downloader uses threads for HTTP downloads and disk writes, but **all DB operations happen on the main thread** after downloads complete:

```python
# Workers: pure I/O, no DB access
def _download_one_thumb(client, guid, dest_dir):
    resp = client.get(url)
    dest.write_bytes(resp.content)
    return (guid, True, None)

# Main thread: batch DB update after all downloads
succeeded = [guid for guid, ok, _ in results if ok]
conn.execute(
    "UPDATE dim_image SET thumb_downloaded = true "
    "WHERE source_image_id IN (SELECT unnest($1::VARCHAR[]))",
    [succeeded],
)
```

This avoids concurrent writes entirely. The DB connection is only touched by the main thread.

### Pattern 2: Check files on disk instead of querying DB

When the download was running and we needed progress, we couldn't query the database. Instead:

```bash
# This works while the DB is locked:
ls D:/artemis/raw/images/thumbs/ | wc -l

# This does NOT work:
artemis-pipeline status  # fails with IO Error
```

The files on disk are the ground truth for download progress. The DB flags are updated in batch after the downloads finish.

### Pattern 3: Background process with finally block

The downloader runs as a background task. If killed mid-download, the `finally` block flushes whatever succeeded to the DB:

```python
try:
    # ... download loop ...
finally:
    if succeeded:
        _flush_succeeded(conn, succeeded)
```

This ensures that even on interrupt, the DB state is updated for completed downloads. On re-run, the query `WHERE thumb_downloaded = false` skips already-processed images.

## Anti-Patterns to Avoid

### Don't open multiple connections from different processes

```python
# Process A (downloader):
conn_a = duckdb.connect("warehouse.duckdb")

# Process B (status check) — THIS WILL FAIL:
conn_b = duckdb.connect("warehouse.duckdb")
```

### Don't pass DuckDB connections to thread workers

```python
# WRONG — conn is not thread-safe for writes
def worker(conn, guid):
    conn.execute("UPDATE dim_image SET ...")  # race condition

with ThreadPoolExecutor() as executor:
    executor.submit(worker, conn, guid)
```

### Don't hold connections open longer than necessary

```python
# BAD — holds lock for entire script duration
conn = get_connection()
# ... 30 minutes of downloads ...
conn.close()

# BETTER — open only when needed
download_files_to_disk()  # no DB needed
conn = get_connection()
batch_update_db(conn)
conn.close()  # lock released
```

## When DuckDB Is the Wrong Choice

If your pipeline needs:
- **Concurrent writes from multiple processes** → Use PostgreSQL or SQLite (WAL mode)
- **Long-running background writes with concurrent reads** → Use a client-server database
- **Real-time monitoring dashboards** → Don't lock the warehouse with a batch writer

DuckDB excels at analytical queries on local data (columnar storage, vectorized execution, zero-dependency embedding). But its single-writer model means you must design pipelines that serialize writes and minimize connection hold time.

## For This Project

DuckDB is the right choice for Artemis because:
- Single-user project (one developer)
- Batch pipeline (writes happen in discrete phases, not continuously)
- Analytical queries (cluster analysis, aggregation, feature store lookups)
- No concurrent write requirements (pipeline steps run sequentially)

The single-writer constraint was only a friction point during development (wanting to check progress while a download ran). In production operation, each pipeline step opens, writes, and closes before the next step starts.

## Related Lessons

- [Read-Only DB for Web Layers](../block5/031_read_only_db_for_web_layers.md) — the web-tier extension of this constraint: open the DB read-only so the pipeline can still write
