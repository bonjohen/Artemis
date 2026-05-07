# Session Startup — Artemis Calendar Image Selection

Use this file to reload context after a `/clear` or new session. Read these files in order.

## 1. Project Context

```
Read CLAUDE.md
```

CLAUDE.md has the full project status, architecture, source site rules, clustering analysis, and design decisions. It is the single source of truth for "where are we."

## 2. Current State

**Phase 2B is complete.** All data collection, feature extraction, and clustering are done.

### Warehouse: `D:/artemis/warehouse.duckdb`

| Table | Rows | What it holds |
|---|---|---|
| `dim_image` | 12,736 | 12,217 vote-pool + 519 editorial images |
| `feature_image_visual` | 12,217 | Brightness, contrast, saturation, dominant colors |
| `feature_image_embedding` | 12,217 | CLIP 512-dim vectors (vote-pool images) |
| `feature_description_embedding` | 502 | Sentence-transformer 384-dim (editorial images with text) |
| `feature_description_text` | 502 | VADER sentiment, TF-IDF topics, entity flags |
| `feature_image_cluster` | 24,936 | k=25 clusters: visual (12,217) + text (502) + multimodal (12,217) |
| `mart_image_cluster_summary` | 75 | 25 clusters x 3 types |
| `mart_cluster_top_images` | 369 | Top 5 images per cluster x 3 types |

### Images: `D:/artemis/raw/images/thumbs/{guid}.jpg`

All 12,217 vote-pool thumbnails are on disk. Full-resolution images (`large/`) are NOT downloaded yet — deferred to Phase C4 (calendar rendering).

### Clustering: k=25, visual-dominant multimodal

- **Weights:** visual 0.80, text 0.05, metadata 0.15
- **Visual clusters:** 25 groups from CLIP embeddings, sizes 77–1,411 (median ~400)
- **Multimodal clusters:** 25 groups from CLIP + metadata (brightness, contrast, saturation, aspect ratio). Text is zero-filled for the 12,217 vote-pool images that lack captions.
- **Text clusters:** 25 groups from the 502 editorial images only (informational, not used for calendar selection)

### Synthetic votes exist

100 synthetic voters, batch/pairwise/category vote fact tables populated. These are for bias detection testing — real votes not yet integrated.

## 3. What Needs to Happen Next

### Phase 3: Statistical Modeling

Build preference scores from vote data:

1. **Elo ratings** from pairwise comparisons (`fact_pairwise_vote`)
2. **Bradley-Terry-Luce** scores from batch ballots (`fact_batch_ballot`)
3. **Bayesian composite scores** combining all vote types
4. **Inter-rater reliability** metrics
5. Backfill `preference_score`, `elo_score`, `borda_score` in `mart_cluster_top_images`

Currently these columns are NULL — Phase 3 populates them.

### Phase 4: Calendar Optimization

Multi-objective optimization to select 13 images:
- Maximize voter preference (from Phase 3 scores)
- Maximize visual diversity (from clustering — no two images from same cluster)
- Cover mission phases (launch, transit, lunar orbit, return)
- Month suitability scoring
- Cover image selection (popularity + cover suitability)

### Shortest path to calendar

1. Phase 3: Statistical modeling (implement `models/` module)
2. Phase 4: Calendar optimization (implement `optimize/` module)
3. C1–C3: Selection, month assignment, cover selection
4. C4: Download full images from NASA, render 8.5x11 pages

## 4. Key Implementation Files

```
Read src/artemis_calendar/cluster/clustering.py     # k-means / HDBSCAN, multimodal weights
Read src/artemis_calendar/cluster/marts.py          # cluster summary + top images mart builders
Read src/artemis_calendar/features/visual.py        # Pillow-based visual features (parallel)
Read src/artemis_calendar/features/embeddings.py    # CLIP + sentence-transformer embeddings
Read src/artemis_calendar/extract/images.py         # concurrent thumbnail downloader
Read src/artemis_calendar/config/settings.py        # paths, rate limits, worker count
Read src/artemis_calendar/cli.py                    # all CLI commands
```

## 5. Quick Data Check

```bash
artemis-pipeline status
```

Or for detailed state:

```python
from artemis_calendar.config.database import get_connection, apply_migrations
conn = get_connection()
apply_migrations(conn)

# Feature extraction completeness
for tbl in ['feature_image_visual', 'feature_image_embedding', 'feature_description_embedding', 'feature_description_text', 'feature_image_cluster']:
    count = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"{tbl}: {count}")

# Cluster distribution
print("\nCluster sizes (visual):")
rows = conn.execute("""
    SELECT cluster_id, count(*) AS n
    FROM feature_image_cluster
    WHERE cluster_type = 'visual'
    GROUP BY 1 ORDER BY 2 DESC
""").fetchall()
for r in rows:
    print(f"  cluster {r[0]:2d}: {r[1]:5d} images")

conn.close()
```

## 6. Key Facts

- **Branch:** main
- **Warehouse:** `D:/artemis/warehouse.duckdb`
- **Images:** `D:/artemis/raw/images/thumbs/{guid}.jpg` (thumbnails), `D:/artemis/raw/images/large/{guid}.JPG` (full — not yet downloaded)
- **12,736 images** in `dim_image`: **12,217 vote-pool** (ART002-E-*) + **519 editorial** (NHQ/KSC-*)
- **8 categories** in `dim_category`
- **Embedding models:** CLIP `openai/clip-vit-base-patch32` (512-dim), sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Embeddings stored as:** DuckDB `FLOAT[]` arrays
- **Multimodal clustering weights:** visual 0.80, text 0.05, metadata 0.15
- **Cluster count:** k=25 (see CLAUDE.md for rationale)
- **Score columns in marts are NULL** until Phase 3 (statistical modeling) backfills them
- **ML deps:** `pip install -e ".[ml]"`
- **NASA rate limit:** 1.0s. Full images NOT needed yet — defer to Phase C4.
