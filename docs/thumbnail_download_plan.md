# Thumbnail Download & Full-Scale Feature Extraction — Implementation Plan

**Source document:** `docs/startup.md`, `CLAUDE.md` (project status section)

## Work Queue Instructions

### State Transitions

Open  ──>  Started  ──>  Completed
              │
              └──>  Blocked  ──>  Started  ──>  Completed

- **Open**: Not yet begun.
- **Started**: Actively in progress. Record the start datetime (PST).
- **Completed**: Done and verified. Record the completion datetime (PST).
- **Blocked**: Cannot proceed; note the blocker in the description.

### Commit Protocol

1. Work through all tasks in a phase.
2. When every task reaches Completed, write the Phase Summary.
3. Stage and commit all changes for the phase. Do not push.
4. Proceed immediately to the next phase.

## Technology Stack (Additive)

| Concern | Choice |
|---|---|
| Image download | `httpx` concurrent via `ThreadPoolExecutor`, HTTP/2, connection pooling |
| Visual features | Pillow (CPU), quantize for dominant colors, `ThreadPoolExecutor` parallelism |
| Image embeddings | CLIP `openai/clip-vit-base-patch32` (512-dim) |
| Text embeddings | `all-MiniLM-L6-v2` (384-dim) |
| Text features | VADER sentiment, TF-IDF, spaCy NER |
| Clustering | scikit-learn k-means, hdbscan |
| Warehouse | DuckDB at `D:/artemis/warehouse.duckdb` |

## Phase 1: Download All Thumbnails

**Goal:** All 12,217 vote-pool thumbnails downloaded to `D:/artemis/raw/images/thumbs/` and `thumb_downloaded = true` in `dim_image`.
**Depends on:** Nothing (first phase).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-07 11:29 AM | 2026-05-07 11:30 AM | Test download with `--limit 50` to verify R2 CDN connectivity and rate limit behavior |
| 1.2 | Completed | 2026-05-07 11:30 AM | 2026-05-07 12:27 PM | Run full thumbnail download with concurrent rewrite (3 workers, 0 delay, 20s timeout) |
| 1.3 | Completed | 2026-05-07 12:27 PM | 2026-05-07 12:27 PM | Verify download count: 12,217/12,217 thumbnails, 0 failures |

### Phase 1 Summary

- **Changes:** Rewrote `download_thumbnails()` in `images.py` for concurrent execution: `ThreadPoolExecutor` with 3 workers, shared `httpx.Client` with HTTP/2 and connection pooling, batch DB updates via `_flush_succeeded()`, single run_manifest record per batch. Added `THUMB_DOWNLOAD_WORKERS` to `settings.py`. Downloaded 12,217 thumbnails (7,798 in final batch at ~50 images/sec, 2.7 min).
- **Commit:** `Rewrite thumbnail downloader for concurrent execution, download all 12K thumbnails`

## Phase 2: Full-Scale Feature Extraction

**Goal:** Visual features, CLIP embeddings, text embeddings, and text features extracted for all downloaded images.
**Depends on:** Phase 1 (thumbnails must exist on disk).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-07 12:42 PM | 2026-05-07 12:44 PM | Extract visual features — replaced sklearn KMeans (147ms/img) with Pillow quantize (0.2ms/img), added ThreadPoolExecutor parallelism, batch DB inserts. 12,217 images processed. |
| 2.2 | Completed | 2026-05-07 12:44 PM | 2026-05-07 12:59 PM | CLIP image embeddings (12,212, ~14 min CPU), text embeddings (492), text features (492) |
| 2.3 | Completed | 2026-05-07 12:59 PM | 2026-05-07 12:59 PM | Verified: feature_image_visual=12,217, feature_image_embedding=12,217, feature_description_embedding=502, feature_description_text=502 |

### Phase 2 Summary

- **Changes:** Optimized `visual.py`: replaced sklearn KMeans dominant color extraction with Pillow quantize (300x faster), single LAB conversion for brightness+contrast, `ThreadPoolExecutor` for parallel feature extraction, `executemany` batch inserts. All 12,217 images have visual features and CLIP embeddings. 502 images with text metadata have text embeddings and text features.
- **Commit:** `Optimize visual feature extraction (300x faster), run full-scale feature extraction`

## Phase 3: Full-Scale Clustering

**Goal:** k-means clustering (visual, text, multimodal) on the full dataset with mart tables built.
**Depends on:** Phase 2 (embeddings must exist).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 3.1 | Completed | 2026-05-07 01:03 PM | 2026-05-07 01:11 PM | k-means clustering: visual=12,217 (25 clusters), text=502 (25 clusters), multimodal=0 (no image_sk overlap between CLIP and text embeddings — pre-existing data issue) |
| 3.2 | Completed | 2026-05-07 01:11 PM | 2026-05-07 01:11 PM | Verified cluster results and mart tables built |
| 3.3 | Completed | 2026-05-07 01:11 PM | 2026-05-07 01:12 PM | 52 tests passing, ruff clean |
| 3.4 | Completed | 2026-05-07 01:12 PM | 2026-05-07 01:12 PM | Stage and commit |

### Phase 3 Summary

- **Changes:** Ran full-scale k-means clustering on 12,217 images (visual) and 502 images (text). Multimodal clustering returned 0 results due to no overlapping `image_sk` between `feature_image_embedding` and `feature_description_embedding` — this is a pre-existing data alignment issue to investigate in a future session.
- **Commit:** `Run full-scale clustering, complete thumbnail download phase`

## Known Issue: Multimodal Clustering

The `feature_image_embedding` and `feature_description_embedding` tables have 0 overlapping `image_sk` values, preventing multimodal clustering. The 502 text-embedded images appear to use different surrogate keys than the 12,217 CLIP-embedded images. This needs investigation — likely a data loading issue where text embeddings were generated from a different `dim_image` snapshot.
