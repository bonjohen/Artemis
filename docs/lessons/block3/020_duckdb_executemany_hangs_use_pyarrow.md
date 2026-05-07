# Lesson 020: DuckDB executemany Hangs — Use PyArrow Bulk Insert

## The Lesson

DuckDB's `executemany` with parameterized INSERT statements can hang indefinitely at scale (10K+ rows). Replacing it with a PyArrow table and `INSERT INTO ... SELECT * FROM tbl` completes the same work in under a second. When DuckDB is your warehouse, bulk writes should go through its columnar ingestion path, not its row-at-a-time parameter binding.

## Context

A data warehouse built on DuckDB (embedded, single-file) needed to write 12,217 preference scores to a mart table. The write function used `conn.executemany(INSERT ..., rows)` — the standard Python DB-API pattern for batch inserts. During development with small test datasets (<100 rows), this worked fine. At full scale, the function hung with no error, no timeout, and no progress — the process consumed CPU but never completed.

## What Happened

1. Built a scoring pipeline that computed composite preference scores for 12,217 images. The write step used `conn.executemany()` with a parameterized INSERT and a list of 12,217 row tuples.
2. At full scale, the function hung after computing all scores. The process stayed alive (consuming CPU) but produced no output and never returned. Killed and retried three times — same behavior every time.
3. Suspected DuckDB lock contention (single-writer constraint) and killed all competing Python processes. Removed stale WAL files. Still hung.
4. Added step-by-step logging around the pipeline. Confirmed the hang occurred specifically at `conn.executemany()` — all upstream computation completed in <1 second.
5. Replaced `executemany` with PyArrow bulk insert: build a `pa.table()` from the row data, then `conn.execute("INSERT INTO mart_table (columns) SELECT * FROM tbl")`. DuckDB natively reads PyArrow tables through its columnar scan path.
6. The PyArrow approach completed in <1 second for all 12,217 rows. The fix was applied to all mart write functions in the project.

## Key Insights

- **`executemany` is not always "batch."** Despite the name, DuckDB's `executemany` may still process rows through the parameter binding path rather than the vectorized columnar engine. For large row counts, this can be catastrophically slower than columnar ingestion — or hang entirely.

- **PyArrow is DuckDB's native bulk format.** DuckDB can scan PyArrow tables directly via its replacement scan feature. Building a `pa.table()` and querying it in SQL is faster than any row-at-a-time approach because it stays in DuckDB's columnar execution model end-to-end.

- **The variable name matters.** DuckDB's Python client resolves Python variable names in SQL queries. `conn.execute("SELECT * FROM tbl")` references the Python variable `tbl`. The variable name `table` is a SQL reserved word and causes a parse error.

- **Column lists prevent default-value mismatches.** When the target table has columns with defaults (like `created_at TIMESTAMPTZ DEFAULT now()`), use `INSERT INTO table (col1, col2, ...) SELECT * FROM tbl` to match the PyArrow columns to specific target columns, skipping the defaulted ones.

- **Test at production scale before shipping.** The hang was invisible at test scale (<100 rows). A single full-scale test run would have caught it immediately.

## Examples

```python
# BEFORE: hangs at 12K+ rows
conn.executemany(
    "INSERT INTO mart_scores (run_id, image_sk, score) VALUES (?, ?, ?)",
    rows,  # 12,217 tuples
)

# AFTER: completes in <1 second
import pyarrow as pa

tbl = pa.table({  # noqa: F841 — referenced by DuckDB SQL
    "run_id": [r[0] for r in rows],
    "image_sk": [r[1] for r in rows],
    "score": [r[2] for r in rows],
})
conn.execute("INSERT INTO mart_scores (run_id, image_sk, score) SELECT * FROM tbl")
```

## Applicability

This applies to any DuckDB write path with 1K+ rows. For smaller datasets (<100 rows), `executemany` works fine and is simpler. The PyArrow pattern is also useful for any database that supports columnar ingestion (e.g., ClickHouse, Snowflake via Arrow Flight).

Does NOT apply to: PostgreSQL/MySQL where `executemany` is well-optimized for parameterized inserts, or streaming scenarios where rows arrive one at a time.

## Related Lessons

- [Batch Database Operations](../block1/batch_db_operations.md) — the general principle of batching DB writes; this lesson adds the DuckDB-specific PyArrow path
- [Per-Record Overhead at Scale](../block1/per_record_overhead_at_scale.md) — the broader pattern of invisible overhead multiplying at scale
