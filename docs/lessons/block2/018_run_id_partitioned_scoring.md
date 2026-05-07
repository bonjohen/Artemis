# Lesson 018: Run-ID Partitioned Scoring

## Problem

The scoring pipeline will be re-run as new vote data arrives, as scoring methods are tuned, or as bugs are fixed. Each run produces a full set of scores for all 12,217 images. If each run overwrites the previous scores, we lose the ability to compare methods, audit changes, or roll back to a known-good state.

## Why It Matters

In a data warehouse, analytical outputs are not code — they can't be version-controlled with git. The warehouse equivalent of version control is **run partitioning**: every analytical output is tagged with a run ID, and consumers explicitly choose which run to read. Without this, a re-run silently replaces all downstream data, and nobody can tell whether a score changed because the method improved or because a bug was introduced.

## Design Choice: Primary Key Includes score_run_id

Every row in `mart_image_preference_score` has a composite primary key of `(score_run_id, image_sk)`. Each scoring run generates a UUID via `generate_run_id()` and writes a complete set of rows tagged with that ID. Previous runs remain in the table untouched.

### How it works in practice

```sql
-- Latest scores for all images
SELECT * FROM mart_image_preference_score
WHERE score_run_id = (
    SELECT score_run_id FROM mart_image_preference_score
    ORDER BY created_at DESC LIMIT 1
);

-- Compare two scoring runs
SELECT a.image_sk, a.posterior_mean AS run_a, b.posterior_mean AS run_b,
       b.posterior_mean - a.posterior_mean AS delta
FROM mart_image_preference_score a
JOIN mart_image_preference_score b USING (image_sk)
WHERE a.score_run_id = 'abc...' AND b.score_run_id = 'def...'
ORDER BY delta DESC;
```

### The cleanup pattern

The pipeline deletes previous rows **for the current run_id only** before inserting:

```python
conn.execute("DELETE FROM mart_image_preference_score WHERE score_run_id = ?", [score_run_id])
```

This means re-running with the same run_id is idempotent (safe to retry after a crash), but different runs accumulate. Table growth is bounded by the number of runs times the number of images — a concern only at scale, easily addressed with a retention policy that drops runs older than N days.

### Run manifest linkage

Each scoring run is also recorded in `run_manifest` with the same run_id, linking the scores to pipeline metadata (start time, completion status, row counts). This closes the audit loop: for any score, you can trace back to when it was computed and whether the pipeline completed successfully.

## Alternatives Considered

1. **Overwrite on each run**: Simpler but loses history. A silent regression in scoring would be undetectable.
2. **Append with timestamp, no run_id**: Works but makes it hard to group a complete set of scores from one run. Timestamps can collide or drift.
3. **Separate tables per run**: Maximum isolation but creates DDL sprawl and makes cross-run queries awkward.
4. **SCD Type 2 (slowly changing dimension)**: Track effective dates per row. Overkill for analytical outputs that are fully replaced each run.

## What Was Learned

Run-ID partitioning is the simplest pattern that gives you both idempotency and auditability. The cost is modest (table grows linearly with runs) and the benefit is large (any score can be traced, compared, or rolled back). The pattern extends naturally to any analytical output — cluster assignments, optimization results, reliability metrics — and the `run_manifest` table serves as the central registry.

The key discipline is: **never query a partitioned table without filtering by run_id**. An unfiltered `SELECT AVG(posterior_mean) FROM mart_image_preference_score` silently averages across all runs, producing garbage. Downstream code should always accept a run_id parameter or default to the most recent.
