# Session Startup — Thumbnail Download & Full-Scale Feature Extraction

Use this file to reload context after a `/clear` or new session. Read these files in order.

## 1. Project Context

```
Read CLAUDE.md
```

CLAUDE.md has the full project status, architecture, source site rules, rate limits, and download strategy. It is the single source of truth for "where are we."

## 2. Active Plan

```
Read docs/thumbnail_download_plan.md
```

This is the active implementation plan. Check which phase/task is currently `Started` or the next `Open` row to know where work left off.

If `docs/thumbnail_download_plan.md` does not exist yet, it needs to be created (Stage 3 per the development workflow in global CLAUDE.md).

## 3. What Needs to Happen

### Step 1: Download all thumbnails (~20–50 min)

```bash
artemis-pipeline collect-images --thumbs-only
```

This downloads 12,212 remaining thumbnails from the R2 CDN (`https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/{guid}.jpg`) at `RATE_LIMIT_R2_CDN` (currently 0.1s). The code in `src/artemis_calendar/extract/images.py` handles resume/dedup — safe to re-run or interrupt.

**Consider:** Raising `RATE_LIMIT_R2_CDN` to 0.2–0.5s for sustained bulk download to avoid Cloudflare bot detection. Monitor for 429 or connection reset errors.

### Step 2: Re-run feature extraction at full scale

```bash
artemis-pipeline extract-visual
artemis-pipeline extract-embeddings
```

`extract-visual` uses Pillow only (fast, ~seconds per 1000 images). `extract-embeddings` runs CLIP (GPU-accelerated if available) and sentence-transformers — budget ~30 min for 12K images on CPU, faster with GPU.

Both commands skip images already processed (dedup by image_sk).

### Step 3: Re-run clustering with full data

```bash
artemis-pipeline run-clustering --algorithm kmeans --cluster-type all --n-clusters 25 --seed 42
```

With 12K+ images, the multimodal clustering (which requires overlapping CLIP + text embeddings) will now have data. Previous cluster results from the 5-image test run can be cleared or will coexist (different cluster_run_id).

### Step 4: Verify and commit

```bash
artemis-pipeline status
pytest --tb=short
ruff check src/ tests/
```

## 4. Key Implementation Files

```
Read src/artemis_calendar/extract/images.py        # thumbnail + full image download
Read src/artemis_calendar/config/settings.py        # RATE_LIMIT_R2_CDN, RATE_LIMIT_NASA, paths
Read src/artemis_calendar/features/visual.py        # Pillow-based visual features
Read src/artemis_calendar/features/embeddings.py    # CLIP + sentence-transformer embeddings
Read src/artemis_calendar/features/text_features.py # VADER sentiment, TF-IDF, entities
Read src/artemis_calendar/cluster/clustering.py     # k-means / HDBSCAN clustering
Read src/artemis_calendar/cluster/marts.py          # cluster summary + top images
Read src/artemis_calendar/cli.py                    # all CLI commands
```

## 5. Data State Check

```bash
artemis-pipeline status
```

Or directly:

```python
from artemis_calendar.config.database import get_connection, apply_migrations
conn = get_connection()
apply_migrations(conn)

# Download progress
total = conn.execute("SELECT count(*) FROM dim_image WHERE vote_pool_flag = true").fetchone()[0]
thumbs = conn.execute("SELECT count(*) FROM dim_image WHERE vote_pool_flag = true AND thumb_downloaded = true").fetchone()[0]
print(f"Thumbnails: {thumbs}/{total} ({total - thumbs} pending)")

# Feature extraction progress
for tbl in ['feature_image_visual', 'feature_image_embedding', 'feature_description_embedding', 'feature_description_text', 'feature_image_cluster']:
    count = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"{tbl}: {count}")
conn.close()
```

## 6. Key Facts

- **Branch:** main
- **Warehouse:** `D:/artemis/warehouse.duckdb`
- **Images:** `D:/artemis/raw/images/thumbs/{guid}.jpg` (thumbnails), `D:/artemis/raw/images/large/{guid}.JPG` (full)
- **12,736 images** in `dim_image`, **12,217 in vote pool**, **8 categories** in `dim_category`
- **Only 5 thumbnails downloaded** — 12,212 pending
- **Synthetic votes exist:** 100 voters, batch/pairwise/category vote fact tables populated
- **Embedding models:** CLIP `openai/clip-vit-base-patch32` (512-dim), sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Embeddings stored as:** DuckDB `FLOAT[]` arrays
- **Multimodal clustering weights:** visual 0.60, text 0.30, metadata 0.10
- **Score columns in marts are NULL** until Phase 3 (statistical modeling) backfills them
- **ML deps are optional:** `pip install -e ".[ml]"`
- **R2 CDN rate limit:** 0.1s (may want 0.2–0.5s for bulk). No robots.txt.
- **NASA rate limit:** 1.0s. Full images NOT needed yet — defer to Phase C4.

## 7. After Thumbnails — Shortest Path to Calendar

1. Download all thumbnails (this session)
2. Run full-scale feature extraction + clustering (this session)
3. **Phase 3:** Statistical modeling — Elo, BTL, Bayesian scores, inter-rater reliability
4. **Phase 4:** Calendar optimization — objective function, month/cover scoring, candidate generation
5. **C1–C3:** Calendar selection, month assignment, cover selection
6. **C4:** Page rendering (needs full images downloaded from NASA)
