# Session Startup — Artemis Calendar Image Selection

Use this file to reload context after a `/clear` or new session. Read these files in order.

## 1. Project Context

```
Read CLAUDE.md
```

CLAUDE.md has the full project status, architecture, source site rules, clustering analysis, and design decisions. It is the single source of truth for "where are we."

## 2. Current State

**Phase 3 is complete.** Data collection, feature extraction, clustering, and statistical modeling are all done.

### Warehouse: `D:/artemis/warehouse.duckdb`

| Table | Rows | What it holds |
|---|---|---|
| `dim_image` | 12,736 | 12,217 vote-pool + 519 editorial images |
| `feature_image_visual` | 12,217 | Brightness, contrast, saturation, dominant colors |
| `feature_image_embedding` | 12,217 | CLIP 512-dim vectors (vote-pool images) |
| `feature_description_embedding` | 502 | Sentence-transformer 384-dim (editorial images with text) |
| `feature_description_text` | 502 | VADER sentiment, TF-IDF topics, entity flags |
| `feature_image_cluster` | 24,936 | k=25 clusters: visual (12,217) + text (502) + multimodal (12,217) |
| `mart_image_cluster_summary` | 75 | 25 clusters x 3 types (preference scores backfilled) |
| `mart_cluster_top_images` | 369 | Top 5 images per cluster x 3 types (scores backfilled) |
| `mart_image_preference_score` | 12,217+ | Per-image composite scores, Elo, Borda, uncertainty, polarization |
| `mart_inter_rater_reliability` | 2+ | Krippendorff's alpha per vote mode |

### Images: `D:/artemis/raw/images/thumbs/{guid}.jpg`

All 12,217 vote-pool thumbnails are on disk. Full-resolution images (`large/`) are NOT downloaded yet — deferred to Phase C4 (calendar rendering).

### Clustering: k=25, visual-dominant multimodal

- **Weights:** visual 0.80, text 0.05, metadata 0.15
- **Visual clusters:** 25 groups from CLIP embeddings, sizes 77–1,411 (median ~400)
- **Multimodal clusters:** 25 groups from CLIP + metadata (brightness, contrast, saturation, aspect ratio). Text is zero-filled for the 12,217 vote-pool images that lack captions.
- **Text clusters:** 25 groups from the 502 editorial images only (informational, not used for calendar selection)

### Preference Scores (Phase 3 output)

Every vote-pool image has a composite preference score in `mart_image_preference_score`:

- **Batch scores:** Selection rate, Wilson lower bound, Beta-Binomial posterior (Beta(2,8) prior) for all 12,217 images
- **Elo scores:** From 2,000 pairwise votes. ~200 images have Elo; rest are NULL (never compared)
- **Borda scores:** From 250 category rankings. ~150 images have Borda; rest are NULL
- **BTL scores:** NULL (deferred — disconnected comparison graph, see lesson 014)
- **Composite:** `posterior_mean` adjusted by Elo/Borda quantile ranks. All images scored.
- **Uncertainty:** Credible interval width. Wide = needs more data.
- **Polarization:** Voter disagreement (std dev of selection outcomes)
- **Broad appeal:** `posterior_mean * (1 - polarization_quantile)`
- **Reliability:** Krippendorff's alpha computed for batch and category vote modes

Score columns in `mart_cluster_top_images` and `mart_image_cluster_summary` are backfilled.

### Synthetic votes

100 synthetic voters (4 profiles: 60% neutral, 20% visual-drama, 10% position-biased, 10% random), batch/pairwise/category vote fact tables populated. Synthetic ground truth in `synthetic_image_truth` for validation.

## 3. What Needs to Happen Next

### Phase 4: Calendar Optimization

Multi-objective optimization to select 13 images (1 cover + 12 monthly pages):

1. **Month suitability scoring** — score each image's fit for each calendar month using visual features (warmth/coolness, brightness, tone), mission phase timing, and seasonal associations
2. **Cover suitability scoring** — score images for cover use (composition, broad appeal, visual impact)
3. **Objective function** — multi-objective balancing:
   - Maximize voter preference (`posterior_mean` from Phase 3)
   - Maximize visual diversity (no two images from same cluster)
   - Cover mission phases (launch, transit, lunar orbit, return)
   - Maximize month-image fit
   - Minimize redundancy (pairwise CLIP similarity penalty)
4. **Candidate generation** — produce ranked calendar slates
5. **Baseline comparison** — compare optimized slate to naive top-13-by-Elo, top-13-by-posterior, etc.

### After Phase 4

| Phase | Description |
|---|---|
| C1–C3 | Selection confirmation, month assignment, cover selection |
| C4 | Download full images from NASA JSC, render 8.5x11 PDF/PNG pages |
| S3–S4 | Synthetic validation: bias detection, optimization validation |
| Phase 5 | Learning and publication package |

### Shortest path to calendar

1. **Phase 4: Calendar optimization** (implement `optimize/` module) ← **YOU ARE HERE**
2. C1–C3: Selection, month assignment, cover selection
3. C4: Download full images from NASA, render 8.5x11 pages

## 4. Key Implementation Files

```
Read src/artemis_calendar/models/__init__.py        # preference scoring orchestrator
Read src/artemis_calendar/models/composite.py       # composite score computation
Read src/artemis_calendar/models/marts.py           # score mart writes + cluster backfill
Read src/artemis_calendar/cluster/clustering.py     # k-means / HDBSCAN, multimodal weights
Read src/artemis_calendar/cluster/marts.py          # cluster summary + top images mart builders
Read src/artemis_calendar/features/visual.py        # Pillow-based visual features (parallel)
Read src/artemis_calendar/features/embeddings.py    # CLIP + sentence-transformer embeddings
Read src/artemis_calendar/config/settings.py        # paths, rate limits, worker count
Read src/artemis_calendar/cli.py                    # all CLI commands (including compute-scores)
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

# Scoring completeness
for tbl in ['mart_image_preference_score', 'mart_inter_rater_reliability']:
    count = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"{tbl}: {count}")

# Score distribution
print("\nComposite score distribution:")
rows = conn.execute("""
    SELECT
        count(*) AS n,
        round(avg(posterior_mean), 4) AS mean,
        round(min(posterior_mean), 4) AS min,
        round(max(posterior_mean), 4) AS max,
        count(elo_score) AS has_elo,
        count(borda_score) AS has_borda
    FROM mart_image_preference_score
    WHERE score_run_id = (
        SELECT score_run_id FROM mart_image_preference_score
        ORDER BY created_at DESC LIMIT 1
    )
""").fetchone()
print(f"  images: {rows[0]}, mean: {rows[1]}, range: [{rows[2]}, {rows[3]}]")
print(f"  with Elo: {rows[4]}, with Borda: {rows[5]}")

# Cluster score backfill check
backfilled = conn.execute("""
    SELECT count(*) FROM mart_cluster_top_images WHERE preference_score IS NOT NULL
""").fetchone()[0]
print(f"\nCluster top images with scores: {backfilled}")

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
- **Scoring:** Beta-Binomial posterior + Elo/Borda quantile adjustments. Run-ID partitioned.
- **68 tests passing** (pytest), ruff clean
- **ML deps:** `pip install -e ".[ml]"`
- **NASA rate limit:** 1.0s. Full images NOT needed yet — defer to Phase C4.

## 7. Design Documents

| Document | Path | Covers |
|---|---|---|
| Calendar product spec | `docs/calendar_design.md` | 13-month layout, page layout, cover selection |
| Physical Design Review | `docs/pdr.md` | Full data model, pipeline architecture, warehouse schema, statistical methods |
| PDR addenda | `docs/pdr_revisions.md` | Archive/refresh, clustering, month/cover scoring, lessons registry |
| Synthetic vote PDR | `docs/synthetic_vote_pdr.md` | Synthetic voter data generator design |
| Feature extraction plan | `docs/feature_extraction_plan.md` | Phase 2A plan (completed) |
| Thumbnail download plan | `docs/thumbnail_download_plan.md` | Phase 2B plan (completed) |
| Statistical modeling design | `docs/statistical_modeling_design.md` | Phase 3 scoring components, composite method, reliability |
| Lessons (block 1) | `docs/lessons/block1/` | 10 lessons from Phases 1–2B |
| Lessons (block 2) | `docs/lessons/block2/` | 8 lessons from Phase 3 (statistical methods + patterns) |
