# Lesson: Per-Record Overhead That Doesn't Matter at 10 Rows Kills You at 12,000

## Problem

The original thumbnail downloader worked flawlessly on 5 images during development. When scaled to 12,217 images, it was unacceptably slow — not because of network latency, but because of per-image overhead that was invisible at small scale.

## Why It Matters

This is the most common performance trap in data pipelines: code that's correct and fast at development scale becomes a bottleneck at production scale. The per-record overhead is often in "bookkeeping" operations that seem cheap individually but multiply catastrophically.

## The Overhead Inventory

For each of the 12,217 thumbnails, the original downloader performed:

| Operation | Time per call | Total for 12,217 | Purpose |
|---|---|---|---|
| New `httpx.Client` (TLS handshake) | 50-200ms | 10-40 min | HTTP connection |
| `generate_run_id()` (UUID) | <0.1ms | negligible | Audit trail |
| `create_run_record()` INSERT | 1-3ms | 12-36 sec | Audit trail |
| `update_run_status()` UPDATE | 1-3ms | 12-36 sec | Audit trail |
| `dim_image` UPDATE | 1-3ms | 12-36 sec | State tracking |
| `run_manifest` UPDATE (checksum) | 1-3ms | 12-36 sec | Audit trail |
| `time.sleep(0.1)` | 100ms | 20 min | Rate limiting |

**Total per-image overhead: ~155-305ms** (excluding network I/O)
**Total for 12,217 images: ~32-62 min of pure overhead**

The actual network download of a 20KB thumbnail takes ~20-50ms. The overhead is 3-15x the useful work.

## What Made It Invisible at Small Scale

At 5 images (the initial test):
- 5 TLS handshakes: ~0.5-1 sec (barely noticeable)
- 5 run_manifest records: ~10ms (instant)
- 5 * 0.1s sleep: 0.5 sec
- Total: ~2-3 seconds. Feels fine.

At 12,217 images: every one of these costs multiplies by 2,443x. The 0.5-second TLS overhead becomes 10+ minutes. The "free" run_manifest records become 36 seconds of DB writes.

## The Fixes (and Their Multipliers)

### 1. Shared HTTP client (biggest win)

```python
# Before: 12,217 TLS handshakes
for guid in guids:
    with httpx.Client() as client:  # new connection each time
        client.get(url)

# After: 1 TLS handshake, reuse connection
with httpx.Client(http2=True) as client:
    for guid in guids:
        client.get(url)  # reuses existing connection
```

**Savings: 10-40 minutes**

### 2. Batch DB writes (second biggest win)

```python
# Before: 4 DB operations per image = 48,868 operations
for guid in guids:
    create_run_record(conn, ...)
    # ... download ...
    update_run_status(conn, ...)
    conn.execute("UPDATE dim_image SET ...")
    conn.execute("UPDATE run_manifest SET ...")

# After: 1 run record + 1 batch UPDATE = ~7 operations
create_run_record(conn, ...)  # one record for entire batch
# ... all downloads ...
conn.execute("UPDATE dim_image SET ... WHERE source_image_id IN (...)", [all_guids])
update_run_status(conn, ...)  # one update
```

**Savings: ~2 minutes of DB I/O, plus eliminates 48,000+ run_manifest rows**

### 3. Eliminate sleep (obvious but requires thought)

```python
# Before: 0.1s sleep per image
time.sleep(RATE_LIMIT_R2_CDN)  # 0.1s * 12,217 = 20 min of sleeping

# After: concurrent workers provide implicit rate limiting
# 3 workers with connection pool = ~3 concurrent requests
# No explicit sleep needed
```

**Savings: 20 minutes of sleeping**

## The Pattern: Audit Trail Overhead

The run_manifest records are a recurring pattern. The manifest design was correct for tracking *pipeline runs* (a metadata collection run, a load batch), where each run is a discrete, meaningful event. But applying the same per-event tracking to 12,217 identical thumbnail downloads produces a table with 12,217 rows that all say the same thing: "downloaded a thumbnail from R2."

### When per-record tracking is worth the cost

- **Heterogeneous operations:** Each record does something different (loading different source files with different schemas)
- **Failure-sensitive operations:** You need to know exactly which record failed and retry it
- **Low volume:** Hundreds of records, not thousands
- **Audit requirements:** Regulatory or compliance reasons require per-record traceability

### When to batch

- **Homogeneous operations:** 12,000 identical downloads from the same host
- **Batch-retryable:** If it fails, just re-run the whole batch (resume handles dedup)
- **High volume:** Thousands of records where per-record overhead dominates
- **No external audit requirement:** Internal pipeline, not compliance-regulated

## Broader Lesson

Before scaling a pipeline from development to production, profile the per-record overhead separately from the per-record useful work:

```python
import time

# Instrument one iteration
t0 = time.time(); setup(); t_setup = time.time() - t0
t0 = time.time(); do_work(); t_work = time.time() - t0
t0 = time.time(); bookkeep(); t_book = time.time() - t0

overhead_ratio = (t_setup + t_book) / t_work
projected_overhead = (t_setup + t_book) * total_records
print(f"Overhead ratio: {overhead_ratio:.1f}x")
print(f"Projected overhead at {total_records} records: {projected_overhead/60:.0f} min")
```

If the overhead ratio is > 1x, you'll spend more time on bookkeeping than on useful work. That's the signal to batch.
