# Lesson: Resume-Safe Pipeline Design — Surviving Interrupts and Partial Failures

## Problem

The thumbnail download process was killed multiple times during development — once to change the rate limit, once to adjust the timeout, once at the user's request. Each time, the question was: how much progress was lost? Can we pick up where we left off?

The answer was "yes" every time — but only because the pipeline was designed for it from the start.

## Why It Matters

Long-running data pipelines (minutes to hours) will be interrupted. Power failures, user cancellation, SSH disconnects, OOM kills, network drops. A pipeline that must restart from zero after every interrupt is a pipeline that never finishes on unreliable data.

## Three Layers of Resume Safety

### Layer 1: Idempotent file writes (on-disk dedup)

The download worker checks if the file already exists before downloading:

```python
def _download_one_thumb(client, guid, dest_dir):
    dest = dest_dir / f"{guid}.jpg"
    if dest.exists():
        return (guid, True, None)  # already on disk, skip download
    # ... download and write ...
```

Files are the first checkpoint. Even if the DB update fails or is never reached, the file on disk proves the download succeeded.

### Layer 2: Database flag filtering (query-level dedup)

The pending image query excludes already-processed images:

```python
query = """
    SELECT source_image_id FROM dim_image
    WHERE vote_pool_flag = true AND thumb_downloaded = false
"""
```

On re-run, images with `thumb_downloaded = true` are never selected. The work list shrinks with each successful batch.

### Layer 3: Graceful flush on interrupt (finally block)

```python
succeeded = []
try:
    with ThreadPoolExecutor() as executor:
        for future in as_completed(futures):
            guid, ok, err = future.result()
            if ok:
                succeeded.append(guid)
finally:
    if succeeded:
        _flush_succeeded(conn, succeeded)
```

Even when killed (KeyboardInterrupt, SIGTERM), the `finally` block writes whatever succeeded to the database. The next run skips those images.

## How the Three Layers Interact

Consider a download of 10,000 images that gets killed at image 6,000:

| Layer | State after kill | State on re-run |
|---|---|---|
| **Files on disk** | 6,000 files exist | Worker sees them, skips download |
| **DB flags** | Depends on flush timing | Query returns only unflagged images |
| **Work list** | Discarded (in memory) | Rebuilt from DB query |

**Best case:** `finally` block ran, DB has 6,000 flags set. Re-run queries for 4,000 remaining.

**Worst case:** `finally` block didn't run (hard kill, OOM). DB still shows 10,000 pending. But the worker checks `dest.exists()` for each, finds 6,000 already on disk, and skips them. The DB flags get updated in the next batch flush. Effective restart point is still 6,000.

The on-disk check is the ultimate safety net. It's slower than the DB check (stat syscall per file vs one SQL query), but it catches the case where the DB is out of sync.

## Design Rules for Resume Safety

### 1. Write the artifact before updating the state

```python
# CORRECT: file exists = work is done
dest.write_bytes(response.content)  # artifact first
conn.execute("UPDATE ... SET done = true")  # state second

# WRONG: state claims work is done, but artifact doesn't exist
conn.execute("UPDATE ... SET done = true")  # state first
dest.write_bytes(response.content)  # artifact second — may never happen
```

If the process dies between the two operations, the first pattern leaves an extra file (harmless), while the second pattern leaves a false flag (data loss).

### 2. Filter by "not done" rather than tracking "what's left"

```python
# CORRECT: query for remaining work each time
pending = conn.execute("SELECT id FROM items WHERE done = false").fetchall()

# FRAGILE: maintain an in-memory work queue
remaining = initial_list.copy()
for item in progress:
    remaining.remove(item)  # lost on kill
```

The "not done" query rebuilds the work list from durable state. An in-memory queue is lost on interrupt.

### 3. Make operations idempotent

Each operation should be safe to repeat:
- **Download:** Skip if file exists. Don't re-download and overwrite.
- **INSERT:** Use `INSERT OR IGNORE`, `ON CONFLICT DO NOTHING`, or check existence before inserting.
- **UPDATE:** Setting `flag = true` when it's already `true` is a no-op. Safe to repeat.
- **DELETE:** Deleting a row that's already deleted is a no-op in most databases.

### 4. Log progress at meaningful intervals

```python
if i % 500 == 0:
    logger.info(f"Progress: {i}/{total}")
```

Progress logs are your audit trail for what happened before a crash. They also help estimate how long a re-run will take.

## Feature Extraction Resume Safety

The same pattern applies to feature extraction. The query filters by what's already processed:

```sql
SELECT di.image_sk FROM dim_image di
WHERE di.thumb_downloaded = true
  AND di.image_sk NOT IN (SELECT image_sk FROM feature_image_visual)
```

If visual extraction is killed at image 8,000, the re-run finds 4,217 remaining and processes only those. No duplicate features, no wasted compute.

## What Resume Safety Costs

- **Extra disk checks:** `dest.exists()` for every image adds ~1ms each. For 12,000 images, that's 12 seconds — negligible compared to download time.
- **Slightly more complex queries:** `NOT IN (SELECT ...)` is slower than a simple `SELECT *`. For 12,000 rows, it adds milliseconds.
- **finally block complexity:** The flush-on-interrupt logic adds ~10 lines of code.

These costs are trivial compared to re-downloading 6,000 images because the pipeline couldn't resume.

## Broader Lesson

Resume safety is cheapest when designed in from the start. Retrofitting it requires understanding all the state transitions and adding checks at each one. The pattern is always the same:

1. **Durable artifact** (file, DB row) marks completion
2. **Query for remaining work** rebuilds the work list from durable state
3. **Idempotent operations** make re-execution safe
4. **Graceful shutdown** flushes partial progress

This applies to any long-running pipeline: ETL jobs, model training checkpoints, migration scripts, backup processes.
