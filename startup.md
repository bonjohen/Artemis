# Session Startup — Artemis Calendar Image Selection

Use this file to reload context after a `/clear` or new session. Read these files in order.

## 1. Project Context

```
Read CLAUDE.md
```

CLAUDE.md has the full project status, architecture, source site rules, clustering analysis, and design decisions. It is the single source of truth for "where are we."

## 2. Current State

**Through Phase C4.** Data collection, feature extraction, clustering, statistical modeling, calendar optimization, and calendar rendering are all complete. Five candidate calendars generated; rendering pipeline produces printable 8.5x11 PDF calendars.

### Warehouse: `D:/artemis/warehouse.duckdb`

| Table | Rows | What it holds |
|---|---|---|
| `dim_image` | 12,736 | 12,217 vote-pool + 519 editorial images |
| `feature_image_visual` | 12,217 | Brightness, contrast, saturation, dominant colors |
| `feature_image_embedding` | 12,217 | CLIP 512-dim vectors (vote-pool images) |
| `feature_description_embedding` | 502 | Sentence-transformer 384-dim (editorial images with text) |
| `feature_description_text` | 502 | VADER sentiment, TF-IDF topics, entity flags |
| `feature_image_cluster` | 24,936 | k=25 clusters: visual (12,217) + text (502) + multimodal (12,217) |
| `mart_image_cluster_summary` | 81 | 25+ clusters x 3 types (preference scores backfilled) |
| `mart_cluster_top_images` | 384 | Top 5 images per cluster x 3 types (scores backfilled) |
| `mart_image_preference_score` | 12,217 | Per-image composite scores, Elo, Borda, uncertainty, polarization |
| `mart_inter_rater_reliability` | 2 | Krippendorff's alpha per vote mode |
| `mart_calendar_candidate` | 5 | One candidate per selection method (A–E) |
| `mart_calendar_candidate_month_image` | 65 | 13 month-image assignments per candidate |

### Images: `D:/artemis/raw/images/thumbs/{guid}.jpg`

All 12,217 vote-pool thumbnails are on disk. Full-resolution images (`large/`) are NOT downloaded yet — deferred to Phase C4 (calendar rendering).

### Clustering: k=25, visual-dominant multimodal

- **Weights:** visual 0.80, text 0.05, metadata 0.15
- **Visual clusters:** 25 groups from CLIP embeddings, sizes 77–1,411 (median ~400)
- **Multimodal clusters:** 25 groups from CLIP + metadata. Text zero-filled for vote-pool images.

### Preference Scores (Phase 3 output)

Every vote-pool image has a composite preference score in `mart_image_preference_score`:

- **Batch scores:** Selection rate, Wilson lower bound, Beta-Binomial posterior (Beta(2,8) prior) for all 12,217 images
- **Elo scores:** From 2,000 pairwise votes. ~394 images have Elo; rest are NULL
- **Borda scores:** From 250 category rankings. ~75 images have Borda; rest are NULL
- **BTL scores:** NULL (deferred — disconnected comparison graph, see lesson 014)
- **Composite:** `posterior_mean` adjusted by Elo/Borda quantile ranks. All images scored.
- **Uncertainty:** Credible interval width. Wide = needs more data.
- **Polarization:** Voter disagreement (std dev of selection outcomes)
- **Broad appeal:** `posterior_mean * (1 - polarization_quantile)`
- **Reliability:** Krippendorff's alpha = 0.52 for batch voting

### Calendar Optimization (Phase 4 output)

Five candidate calendars in `mart_calendar_candidate`, each with 13 month-image assignments:

| Method | Objective | Popularity | Diversity | Description |
|---|---|---|---|---|
| **method_b** | **14.259** | 4.316 | 0.846 | Top popularity with max 2 per cluster |
| method_a | 14.187 | **4.324** | 0.769 | Naive top 13 by posterior_mean |
| method_c | 13.957 | 4.013 | **1.000** | Best image from top 13 clusters |
| method_d | 13.219 | 3.113 | 0.615 | Best image per month by month-fit |
| method_e | 11.885 | 2.791 | 0.769 | MMR greedy (0 overlap with method_a) |

Method B scored highest overall. Method A and E share 0 of 13 images — the optimizer selects genuinely different images.

### Synthetic votes

100 synthetic voters (4 profiles: 60% neutral, 20% visual-drama, 10% position-biased, 10% random), batch/pairwise/category vote fact tables populated. Synthetic ground truth in `synthetic_image_truth` for validation.

## 3. What Needs to Happen Next

### Phase C4: Calendar Rendering — DONE

Rendering pipeline complete. Run `artemis-pipeline render-calendar --candidate method_b` to render.

- `render/layout.py` — Page constants (2550x3300 at 300 DPI), font loading (Segoe UI)
- `render/grid.py` — Calendar grid with Sunday start, correct day-of-week alignment
- `render/page.py` — Monthly page (image + grid + optional description) and cover page (full-bleed + title overlay)
- `render/pipeline.py` — Orchestrator: query candidate data, download 13 full-res images, render pages, combine into PDF
- `extract/images.py` — `download_candidate_images()` for targeted 13-image download from NASA JSC
- Output: `D:/artemis/output/calendars/{candidate_name}/` with PNGs, individual PDFs, and combined `calendar.pdf`

### Phase C5: Review Package — NEXT

| Phase | Description |
|---|---|
| C5 | Review package: candidate comparison, contact sheet, selection report, layout validation |
| S3–S4 | Synthetic validation: bias detection, optimization validation |
| Phase 5 | Learning and publication package |

### Shortest path to printed calendar

1. ~~Phase C4: Calendar rendering~~ DONE
2. **C5: Review package and final export** ← **YOU ARE HERE**
3. Print

## 4. Key Implementation Files

```
Read src/artemis_calendar/optimize/__init__.py    # calendar optimization orchestrator
Read src/artemis_calendar/optimize/methods.py     # 5 selection methods (A–E)
Read src/artemis_calendar/optimize/month_fit.py   # month suitability scoring + CALENDAR_MONTHS constant
Read src/artemis_calendar/optimize/assignment.py  # Hungarian month assignment
Read src/artemis_calendar/optimize/scoring.py     # calendar-level scoring
Read src/artemis_calendar/optimize/cover_fit.py   # cover suitability scoring
Read src/artemis_calendar/optimize/marts.py       # write candidates to warehouse
Read src/artemis_calendar/models/__init__.py      # preference scoring orchestrator
Read src/artemis_calendar/models/composite.py     # composite score computation
Read src/artemis_calendar/models/marts.py         # score mart writes (PyArrow bulk insert)
Read src/artemis_calendar/render/__init__.py       # render_calendar entry point
Read src/artemis_calendar/render/layout.py         # page constants, font loading
Read src/artemis_calendar/render/grid.py           # calendar grid renderer
Read src/artemis_calendar/render/page.py           # month page + cover page composition
Read src/artemis_calendar/render/pipeline.py       # rendering orchestrator (query, download, render, PDF)
Read src/artemis_calendar/config/settings.py       # paths, rate limits, OUTPUT_ROOT
Read src/artemis_calendar/cli.py                   # all CLI commands including render-calendar
```

## 5. Quick Data Check

```bash
artemis-pipeline status
```

Or for detailed optimization state:

```python
from artemis_calendar.config.database import get_connection, apply_migrations
conn = get_connection()
apply_migrations(conn)

# Calendar candidates
print("=== Calendar Candidates ===")
rows = conn.execute("""
    SELECT candidate_name, objective_score, popularity_score, diversity_score,
           month_fit_score, cover_image_sk
    FROM mart_calendar_candidate
    ORDER BY objective_score DESC
""").fetchall()
for r in rows:
    print(f"  {r[0]:<12} obj={r[1]:.3f} pop={r[2]:.3f} div={r[3]:.3f} mfit={r[4]:.3f} cover={r[5]}")

# Best candidate month assignments
print("\n=== Best Candidate (method_b) Month Assignments ===")
rows = conn.execute("""
    SELECT sequence_number, month_label, image_sk,
           month_fit_score, preference_score
    FROM mart_calendar_candidate_month_image
    WHERE candidate_name = 'method_b'
    ORDER BY sequence_number
""").fetchall()
for r in rows:
    print(f"  Seq {r[0]:>2}: {r[1]:<18} sk={r[2]:>6} mfit={r[3]:.3f} pref={r[4]:.4f}")

# Scoring completeness
for tbl in ['mart_image_preference_score', 'mart_inter_rater_reliability']:
    count = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"\n{tbl}: {count}")

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
- **Optimization:** 5 methods, Hungarian month assignment, PyArrow bulk insert for all mart writes
- **Rendering:** Pillow-based, 2550x3300 px (300 DPI), Segoe UI fonts, multi-page PDF via `Image.save(save_all=True)`
- **Output:** `D:/artemis/output/calendars/{candidate_name}/` — PNGs, individual PDFs, combined `calendar.pdf`
- **96 tests passing** (pytest), ruff clean
- **ML deps:** `pip install -e ".[ml]"` (includes scipy>=1.12)
- **NASA rate limit:** 1.0s per request. Full images needed only for the 13 selected images.

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
| Calendar optimization design | `docs/calendar_optimization_design.md` | Phase 4: month-fit, cover-fit, 5 methods, objective function |
| Calendar rendering plan | `docs/calendar_rendering_plan.md` | Phase C4: layout, grid, page composition, targeted download, PDF assembly |
| Lessons (block 1) | `docs/lessons/block1/` | 10 lessons from Phases 1–2B (infrastructure, scaling, DuckDB) |
| Lessons (block 2) | `docs/lessons/block2/` | 8 lessons from Phase 3 (statistical methods + patterns) |
| Lessons (block 3) | `docs/lessons/block3/` | 8 lessons from Phase 4 (optimization, PyArrow, MMR, assignment) |
