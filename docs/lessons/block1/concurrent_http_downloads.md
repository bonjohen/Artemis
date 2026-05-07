# Lesson: Concurrent HTTP Downloads with Connection Pooling

## Problem

The original thumbnail downloader processed 12,217 images sequentially. Each download created a new `httpx.Client` instance, which meant a fresh TCP connection and TLS handshake for every single request — all to the same Cloudflare R2 CDN endpoint. At 0.1s rate limiting plus ~50-200ms connection overhead per image, the full download was projected at 20-50 minutes.

## Why It Matters

Sequential HTTP downloads to a single host is one of the most common performance anti-patterns in data pipelines. The cost isn't just the network latency — it's the repeated connection setup. A TLS 1.3 handshake to Cloudflare takes 50-200ms depending on the client. Multiply that by 12,000 and you've added 10-40 minutes of pure overhead that does nothing useful.

## What Happened

<!-- reconstructed from git history (3234106, 9ad5892) and lesson context -->

1. Built the initial thumbnail downloader as a sequential loop. Each iteration created a new `httpx.Client`, downloaded one image, performed 4 DB operations, and called `time.sleep(0.1)` for rate limiting. Tested on 5 images — worked perfectly in ~2 seconds.
2. Projected the time for 12,217 images: 20-50 minutes. The dominant cost was not network latency (20KB thumbnails download in ~20-50ms each) but per-image connection overhead — a fresh TLS 1.3 handshake to Cloudflare R2 on every single request.
3. Redesigned around three independent optimizations: shared `httpx.Client` with HTTP/2 connection pooling (one TLS handshake instead of 12,217), `ThreadPoolExecutor(max_workers=3)` for concurrent I/O, and batch DB updates after all downloads complete.
4. Chose 3 workers deliberately — respectful of the CDN without being needlessly slow. No rate-limit headers from R2, but 20 concurrent connections risks bot detection on a free public bucket.
5. Chose `ThreadPoolExecutor` over `asyncio` because the entire codebase is synchronous. Threading parallelizes I/O without requiring an architectural rewrite. Workers do pure network + disk I/O; the main thread handles all DuckDB writes (single-writer constraint).
6. First run downloaded 7,798 images in 2.7 minutes (~50 images/sec, zero failures). Second run completed the remaining 4,419 images, demonstrating the resume-safe design. Total: 12,217 thumbnails with 0 failures.

## The Fix

Three changes, each independently valuable but multiplicative together:

### 1. Shared `httpx.Client` with connection pooling

```python
with httpx.Client(
    timeout=20.0,
    http2=True,
    limits=httpx.Limits(max_connections=3, max_keepalive_connections=3),
) as client:
    # All downloads reuse this client's connection pool
```

One TLS handshake, then HTTP/2 multiplexing over the same connection. The `limits` parameter caps concurrent connections to match the worker count.

**Key insight:** `httpx.Client` is thread-safe for `.get()` calls. You can pass one shared client to multiple threads.

### 2. `ThreadPoolExecutor` for concurrent downloads

```python
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(_download_one_thumb, client, guid, dest_dir): guid
        for guid in guids
    }
    for future in as_completed(futures):
        guid, ok, err = future.result()
```

Workers are pure I/O (HTTP GET + write bytes to disk). No DB access in the worker — this is critical for DuckDB, which is single-writer.

### 3. Batch DB updates after downloads

Instead of 4 DB operations per image (run_manifest create, run_manifest update, dim_image update, optional exists check), all successful GUIDs are collected in a list and flushed in one batch:

```python
conn.execute(
    "UPDATE dim_image SET thumb_downloaded = true, updated_at = now() "
    "WHERE source_image_id IN (SELECT unnest($1::VARCHAR[]))",
    [chunk_list],
)
```

One run_manifest record for the entire batch instead of 12,000 individual records.

## Results

| Metric | Before | After |
|---|---|---|
| Connection overhead | ~50-200ms per image (new TLS each time) | ~50-200ms once (shared client) |
| Concurrency | 1 (sequential) | 3 workers |
| DB operations per image | 4 | 0 (batched at end) |
| Run manifest records | 12,000 | 1 |
| Time for 7,798 images | ~13 min (projected) | 2.7 min |
| Throughput | ~10 images/sec | ~50 images/sec |

## Design Decisions

**Why 3 workers, not 20?** The user chose 3 to be respectful of the CDN. Even with no rate limiting headers from Cloudflare R2, hammering a free public bucket with 20 concurrent connections risks triggering bot detection. 3 workers achieved 50 images/sec with zero failures — there was no need to be more aggressive.

**Why `ThreadPoolExecutor`, not `asyncio`?** The project is 100% synchronous. Converting to async would have required rewriting the entire call chain (CLI → download → DB). Threads work well for I/O-bound downloads and `httpx.Client` is thread-safe. The pragmatic choice was to parallelize at the smallest scope rather than refactor the architecture.

**Why separate download from DB writes?** DuckDB is single-writer. Concurrent writes from multiple threads cause lock conflicts. The clean pattern is: workers do pure I/O (network + disk), main thread does all DB writes after collection. This also provides natural crash recovery — if the process dies mid-download, the files are on disk and a re-run will pick them up (the worker checks `dest.exists()` before downloading).

## Gotcha: DuckDB Connection Locking

DuckDB holds an exclusive file lock while a connection is open. During the background download, no other process can open `warehouse.duckdb`. This means you can't run `artemis-pipeline status` to check progress while a download is running. The workaround is checking file count on disk (`ls D:/artemis/raw/images/thumbs/ | wc -l`) instead of querying the database.

## Applicability

This pattern applies whenever you're downloading many files from the same host:
- Model weights from Hugging Face
- Dataset files from S3/GCS/R2
- API pagination (many small requests to the same endpoint)
- Web scraping with respectful rate limiting

The three ingredients — shared client, thread pool, batch DB — are independent and can be applied individually. Even just switching from a new client per request to a shared client can cut download time by 30-50%.
