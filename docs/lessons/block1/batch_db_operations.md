# Lesson: Batch Database Operations — INSERT/UPDATE Patterns at Scale

## Problem

Multiple pipeline stages in Artemis started with per-row INSERT or UPDATE patterns that worked fine during development (5-10 rows) but became bottlenecks at full scale (12,000+ rows). The per-row pattern appeared in three places:

1. **Thumbnail downloader:** 4 DB operations per image (run_manifest create + update, dim_image update, checksum update)
2. **Visual feature extraction:** Per-image INSERT into `feature_image_visual`
3. **Cluster result writing:** Per-image INSERT into `feature_image_cluster`

## Why It Matters

Database round-trips have fixed overhead: query parsing, plan optimization, lock acquisition, transaction commit, and network latency (even for embedded databases like DuckDB). At 1-3ms per operation, 12,000 individual INSERTs take 12-36 seconds of pure overhead. Batching amortizes this overhead across thousands of rows.

## Three Batching Patterns Used

### Pattern 1: `executemany` for homogeneous INSERTs

When inserting many rows with the same structure, `executemany` sends one prepared statement with multiple parameter sets:

```python
# Before: 12,217 individual INSERTs
for image_sk, run_id, orientation, ... in results:
    conn.execute(
        "INSERT INTO feature_image_visual (...) VALUES (?, ?, ?, ...)",
        [image_sk, run_id, orientation, ...],
    )

# After: batch INSERT with executemany
from itertools import batched
for chunk in batched(results, 2000):
    conn.executemany(
        "INSERT INTO feature_image_visual (...) VALUES (?, ?, ?, ...)",
        list(chunk),
    )
```

**Why chunk at 2000?** DuckDB handles large batches well, but chunking provides progress visibility and bounds memory usage. The chunk size is not performance-critical — 500, 2000, or 5000 all work. The key is not doing 12,000 individual calls.

### Pattern 2: `UPDATE ... WHERE IN (unnest)` for batch flag updates

When updating a boolean flag for many known IDs:

```python
# Before: 12,217 individual UPDATEs
for guid in succeeded:
    conn.execute(
        "UPDATE dim_image SET thumb_downloaded = true WHERE source_image_id = ?",
        [guid],
    )

# After: batch UPDATE with array unnest
for chunk in batched(succeeded, 2000):
    conn.execute(
        "UPDATE dim_image SET thumb_downloaded = true, updated_at = now() "
        "WHERE source_image_id IN (SELECT unnest($1::VARCHAR[]))",
        [list(chunk)],
    )
```

The `unnest($1::VARCHAR[])` pattern passes a Python list as a single parameter and expands it server-side. This is DuckDB-specific syntax — PostgreSQL would use `= ANY($1)`, SQLite would need a temp table or dynamic SQL.

### Pattern 3: Single aggregate record instead of per-item records

When audit trail granularity doesn't need to be per-item:

```python
# Before: 12,217 run_manifest records
for guid in guids:
    run_id = generate_run_id()
    create_run_record(conn, run_id=run_id, source_name=guid, ...)
    # ... download ...
    update_run_status(conn, run_id, ...)

# After: 1 run_manifest record for the batch
run_id = generate_run_id()
create_run_record(conn, run_id=run_id, source_name=f"batch-{len(guids)}", ...)
# ... all downloads ...
update_run_status(conn, run_id, row_count_raw=len(succeeded), ...)
```

This eliminates both the INSERT overhead (12,217 → 1) and the storage cost (12,217 rows → 1 row in run_manifest).

## Performance Comparison

Measured on the Artemis pipeline (DuckDB, local SSD, 12,217 images):

| Pattern | Operations | Time |
|---|---|---|
| Per-row INSERT (feature_image_visual) | 12,217 | ~15-20 sec |
| executemany in 2000-row chunks | 7 | < 1 sec |
| Per-row UPDATE (dim_image flags) | 12,217 | ~15-20 sec |
| Batch UPDATE with unnest | 7 | < 1 sec |
| Per-row run_manifest create + update | 24,434 | ~30-40 sec |
| Single batch record | 2 | < 0.01 sec |

## When NOT to Batch

- **When you need per-row error handling:** If each INSERT might fail independently (constraint violation, data quality issue) and you need to log which specific row failed, per-row execution with try/except is appropriate.
- **When rows arrive one at a time:** Streaming pipelines process rows as they arrive. Batching requires buffering, which adds latency and memory pressure.
- **When the batch is small:** For < 100 rows, the overhead difference is negligible. Don't add batching complexity for small datasets.

## DuckDB-Specific Notes

- **`executemany` is well-optimized in DuckDB.** It's not just a loop over `execute` — DuckDB batches the parameter binding and executes as a single vectorized operation.
- **`unnest` with typed arrays** (`$1::VARCHAR[]`) is the idiomatic way to pass lists in DuckDB. Avoid string-building `IN ('{a}', '{b}', ...)` which is both slower and a SQL injection risk.
- **Transaction scope:** DuckDB auto-commits each statement by default. For large batches, wrapping in an explicit transaction can help: `conn.execute("BEGIN"); ... conn.execute("COMMIT")`.
- **`itertools.batched`** (Python 3.12+) is the cleanest way to chunk. For older Python, use a simple generator or `more_itertools.chunked`.

## Broader Lesson

The default pattern in most tutorials is per-row operations inside a loop. This is correct for learning but wrong for production. Any time you see this pattern at scale:

```python
for item in large_collection:
    db.execute("INSERT/UPDATE ...", [item.field1, item.field2])
```

Replace it with a batch pattern. The specific syntax varies by database, but the principle is universal: amortize per-operation overhead across many rows.
