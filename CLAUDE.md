# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Artemis is a data science and data engineering platform for selecting a high-quality **Artemis II 13-month calendar image collection** (December 2026 through December 2027). The core problem is **collection optimization, not top-N ranking** — selecting 13 images that work together as a calendar (1 cover + 12 monthly pages), balancing voter preference, visual diversity, mission coverage, month suitability, and redundancy control.

The project sources imagery and voting data from ArtemisTimeline.com, which hosts ~12,000 Artemis II mission photos with three voting modes: random-batch (50 shown, pick 5), head-to-head Elo, and category top-3 ranking.

## Project Status

**Through Phase S3-S4.** Data pipeline, synthetic votes, feature extraction, clustering, statistical modeling, calendar optimization, calendar rendering, review package, and synthetic validation are all complete. Five candidate calendars generated with comparison scorecard, contact sheets, selection reports, layout validation diagnostics, and final export package. Bias detection (position bias, cluster bias, voter segmentation, score-truth correlation, reliability under bias) and calendar optimization validation (ground-truth recovery, slate diversity) are implemented and tested.

### What exists

| Layer | Status |
|---|---|
| Extract / parse / load pipeline | Working — metadata, images (concurrent downloader), vote manifest |
| Warehouse (`D:/artemis/warehouse.duckdb`) | 29 tables, `dim_image` 12,736 rows, full scoring + optimization |
| Thumbnails | **All 12,217** vote-pool thumbnails downloaded to `D:/artemis/raw/images/thumbs/` |
| Feature extraction | `features/visual.py` (Pillow, parallel), `features/embeddings.py` (CLIP 512-dim + sentence-transformers 384-dim), `features/text_features.py` (VADER, TF-IDF, entities) |
| Clustering | `cluster/clustering.py` (k-means, HDBSCAN), `cluster/marts.py` (summary + top images). Full-scale k=25 clustering complete |
| Statistical modeling | `models/` — Beta-Binomial, Elo, Borda, composite scoring, inter-rater reliability. All 12,217 images scored |
| Calendar optimization | `optimize/` — 5 selection methods (top-N, cluster-limited, per-cluster, month-first, MMR greedy), Hungarian month assignment, calendar-level scoring. 5 candidate calendars generated |
| Calendar rendering | `render/` — layout constants, calendar grid renderer, monthly page + cover page composition, targeted image download, multi-page PDF assembly. CLI: `render-calendar` |
| Review package | `review/` — candidate comparison scorecard, contact sheets (4x4 grid), selection reports (per-image rationale + cluster alternatives), layout validation (aspect ratio, brightness, color, cluster overlap), export assembly. CLI: `review-package` |
| Synthetic validation | `validate/bias_detection.py` (position bias, cluster bias, voter segments, score-truth correlation, reliability under bias), `validate/calendar_validation.py` (ground-truth recovery, slate diversity, method comparison). CLI: `validate-bias`, `validate-calendar` |
| Lessons viewer | `docs/lessons/lessons.html` — static web viewer with card grid, category filtering, dark mode. `lesson.html` renders markdown via marked.js. Atlas design system (`system/tokens.css`, `system/system.css`) |
| CLI commands | `migrate`, `status`, `collect-metadata`, `load-metadata`, `collect-images`, `generate-votes`, `extract-visual`, `extract-embeddings`, `run-clustering`, `compute-scores`, `optimize`, `render-calendar`, `review-package`, `validate-bias`, `validate-calendar`, `run-all` |
| Tests | 131 passing (pytest), ruff clean |

### Current data state

| Table | Rows | Notes |
|---|---|---|
| `dim_image` | 12,736 | 12,217 vote-pool + 519 editorial |
| `feature_image_visual` | 12,217 | Brightness, contrast, saturation, dominant colors |
| `feature_image_embedding` | 12,217 | CLIP 512-dim vectors |
| `feature_description_embedding` | 502 | Sentence-transformer 384-dim (editorial images with text only) |
| `feature_description_text` | 502 | VADER sentiment, TF-IDF topics, entity flags |
| `feature_image_cluster` | 24,936 | 3 cluster types x ~12K/502 images each |
| `mart_image_cluster_summary` | 81 | 25+ clusters x 3 types (preference scores backfilled) |
| `mart_cluster_top_images` | 384 | Top 5 per cluster x 3 types (scores backfilled) |
| `mart_image_preference_score` | 12,217 | Composite scores, Elo, Borda, uncertainty, polarization |
| `mart_inter_rater_reliability` | 2 | Krippendorff's alpha per vote mode |
| `mart_calendar_candidate` | 5 | One per selection method (A–E) |
| `mart_calendar_candidate_month_image` | 65 | 13 month-image assignments per candidate |
| `mart_bias_detection` | 0* | Position/cluster/voter bias detection results |
| `mart_calendar_validation` | 0* | Ground-truth recovery and diversity per method |

### Two image populations in dim_image

| Population | image_sk range | Count | vote_pool | Has thumbnails | Has titles/descriptions |
|---|---|---|---|---|---|
| Editorial (NASA press) | 13256–13774 | 519 | false | No | 502 yes |
| Mission photos (ART002-E-*) | 13775–25991 | 12,217 | true | Yes (all) | No |

Vote-pool images have CLIP embeddings but no text metadata. Editorial images have text but no thumbnails. This is why text embeddings cover only 502 images and multimodal clustering zero-fills text for the 12,217 vote-pool images.

### Design documents

- `docs/calendar_design.md` — Calendar product spec (13-month layout, page layout, cover selection)
- `docs/pdr.md` — Physical Design Review: full data model, pipeline architecture, warehouse schema, statistical methods, acceptance criteria
- `docs/pdr_revisions.md` — Addenda: archive/refresh pipeline, clustering design, month/cover scoring, lessons-learned registry, Pipeline Explorer
- `docs/synthetic_vote_pdr.md` — Synthetic voter data generator design for bias detection testing
- `docs/feature_extraction_plan.md` — Phase 2A plan (all 5 phases completed)
- `docs/thumbnail_download_plan.md` — Thumbnail download and full-scale feature extraction plan (all 3 phases completed)
- `docs/statistical_modeling_design.md` — Phase 3 scoring components, composite method, reliability
- `docs/calendar_optimization_design.md` — Phase 4 optimization: month-fit, cover-fit, 5 selection methods, objective function
- `docs/calendar_rendering_plan.md` — Phase C4 rendering: layout, grid, page composition, targeted download, PDF assembly

## Architecture

The project follows a **JobClass-style layered warehouse pattern** (modeled after `github.com/bonjohen/jobclass`):

**Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports**

Package layout under `src/artemis_calendar/`:

| Module | Status | Purpose |
|---|---|---|
| `config/` | Exists | Source manifests, settings, paths, database connection |
| `extract/` | Exists | Download source pages, manifests, images (concurrent), vote data |
| `parse/` | Exists | Source-specific parsers (timeline, category, leaderboard, vote manifest) |
| `load/` | Exists | Staging and warehouse loaders |
| `validate/` | Exists | `checks.py` (row counts, duplicates), `bias_detection.py` (S3), `calendar_validation.py` (S4), `marts.py` |
| `observe/` | Exists | Run manifests, structured JSON logging |
| `features/` | Exists | Image/text embeddings, sentiment, visual features (parallel extraction) |
| `cluster/` | Exists | Visual, text, and multimodal clustering + mart builders |
| `synthetic/` | Exists | Voter profiles, ground truth, vote generator |
| `models/` | Exists | Preference scoring (Elo, Borda, Beta-Binomial), composite scores, reliability |
| `optimize/` | Exists | Calendar slate generation, month/cover scoring, 5 selection methods, Hungarian assignment |
| `render/` | Exists | Calendar page rendering: layout, grid, monthly/cover pages, pipeline, PDF assembly |
| `review/` | Exists | Review package: comparison, contact sheet, selection report, validation, export |
| `marts/` | Not started | Analytical outputs (beyond cluster/scoring/calendar marts) |
| `reports/` | Not started | Review packages (superseded by `review/` for C5 deliverables) |

## Clustering Analysis

### Why k=25?

The k-means clustering uses k=25 clusters for 12,217 images. This number was chosen to balance several competing goals for calendar selection:

**Practical calendar constraint.** The calendar needs 13 images. With 25 clusters, each cluster averages ~489 images. Selecting 1 image from roughly every other cluster gives the calendar guaranteed visual diversity — no two monthly images will come from the same visual neighborhood. If k were smaller (say 10), each cluster would be too broad to distinguish meaningfully different image types. If k were larger (say 100), many clusters would have too few images to offer meaningful choice, and the optimization problem becomes over-constrained.

**Rule of thumb for k-means.** A common heuristic is k ≈ √(n/2). For n=12,217 that gives k ≈ 78, which is an upper bound. For calendar selection we want interpretable, visually distinct groups — not maximum granularity — so we pull k well below this ceiling.

**Cluster size distribution.** The actual distribution ranges from 77 images (smallest) to 1,411 (largest), with a median around 400. This spread is healthy — it means the CLIP embedding space has a few dominant visual themes (likely Earth views and dark space scenes) and many smaller distinctive groupings (crew shots, hardware details, specific orbital perspectives). The large clusters will need sub-sampling during optimization; the small clusters represent rare and potentially high-value diversity.

**Multimodal weighting.** Multimodal clustering uses weights of 0.80 visual / 0.05 text / 0.15 metadata. This is visual-dominant because voters choose by appearance, not captions. The metadata features (brightness, contrast, saturation, aspect ratio) add perceptual signal that CLIP alone may underweight — two images might look similar to CLIP but one is dramatically brighter or more saturated. Text is nearly zero-weighted because only 502 of 12,217 images have text, and those 502 aren't even in the vote pool.

### Three clustering views

| Type | Images | What it captures |
|---|---|---|
| **Visual** | 12,217 | Pure CLIP similarity — scene content, composition, color palette |
| **Text** | 502 | Semantic grouping by caption/description (editorial images only) |
| **Multimodal** | 12,217 | CLIP + perceptual metadata (brightness, contrast, saturation, aspect ratio) |

The visual and multimodal clusterings cover the full vote pool and are the ones that matter for calendar optimization. Text clustering is informational only — it groups the 502 editorial images by what they depict according to their captions.

## Source Sites and Download Rules

Three upstream sources serve image data. All permit automated access but require respectful rate limiting.

### R2 CDN — Thumbnails (primary for feature extraction)

- **Base URL:** `https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/{guid}.jpg`
- **robots.txt:** No robots.txt (404). Cloudflare R2 public bucket.
- **Our approach:** Concurrent download with 3 workers, shared `httpx.Client` with HTTP/2 and connection pooling. No per-request delay. All 12,217 thumbnails downloaded successfully (0 failures, ~2.7 min).
- **Thumbnail size:** ~20 KB avg. Total: ~234 MB.

### NASA JSC — Full-Resolution Images

- **Base URL:** `https://eol.jsc.nasa.gov/DatabaseImages/ESC/large/ART002/{guid}.JPG`
- **robots.txt:** `User-agent: * / Sitemap: ...` (no Disallow — full access permitted).
- **License:** NASA imagery is not copyrighted. Attribution required: "Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center" with photo ID and eol.jsc.nasa.gov URL.
- **Restrictions:** Do not imply NASA endorsement. No commercial use of recognizable people without consent.
- **Our rate limit:** `RATE_LIMIT_NASA = 1.0s` in `config/settings.py`. NASA servers are older and slower — do not go below 1.0s.
- **Full image size:** ~600 KB avg. Total: ~7 GB. **Full images are NOT needed for feature extraction or clustering** — thumbnails suffice. Only download full images for final calendar rendering (Phase C4).

### ArtemisTimeline.com — Metadata and Vote Manifest

- **robots.txt:** `User-agent: * / Allow: / / Sitemap: ...`
- **License:** Site code is MIT (github.com/hankmt/Artemis-Timeline). Image data sourced from NASA.
- **API:** Cloudflare Workers at `photovote-api.hankmt.workers.dev` (leaderboard, elo-top, count endpoints). No documented rate limits, but these are lightweight JSON endpoints on a free-tier worker — keep requests sparse.
- **Manifest:** `vote/manifest.json` (12,217 items) already archived at `D:/artemis/raw/artemistimeline/vote_manifest/`.

## Key Design Decisions

- **Immutable raw archive**: Every source snapshot preserved with content hash, never modified after capture
- **Natural grain preservation**: Vote events stored at their native grain (batch ballots, pairwise comparisons, category rankings) — not collapsed into single scores prematurely
- **Surrogate voter keys**: Anonymous voter continuity via `voter_sk` + hashed source IDs; no PII storage
- **Dual operating modes**: Full raw-vote mode (if data is provided) and aggregate-only fallback mode
- **Calendar as portfolio optimization**: Multi-objective function balancing preference, diversity, month fit, cover fit, mission coverage, minus redundancy/uncertainty penalties
- **13-image calendar**: Cover image must be one of the 13 monthly images, selected by composite popularity + cover suitability score
- **Visual-dominant clustering**: Multimodal weights 0.80 visual / 0.05 text / 0.15 metadata — voters choose by appearance, text is optional and sparse
- **Concurrent downloads**: Thumbnail downloader uses `ThreadPoolExecutor` with shared `httpx.Client` (HTTP/2, connection pooling) and batch DB updates
- **Fast visual features**: Pillow quantize for dominant colors (~0.2ms/image) instead of sklearn KMeans (~147ms/image)
- **PyArrow bulk insert for DuckDB**: `pa.table()` + `INSERT ... SELECT * FROM tbl` instead of `executemany` which hangs at 12K+ rows
- **MMR greedy for diversity**: Maximum marginal relevance with CLIP cosine similarity produces 0-overlap vs. naive top-N in <1 second
- **Hungarian month assignment**: `scipy.optimize.linear_sum_assignment` for provably optimal image-to-month mapping

## Data Model Conventions

| Prefix | Object Type |
|---|---|
| `raw_` | Raw source tables |
| `stg_` | Staging tables |
| `dim_` | Dimension tables |
| `fact_` | Fact tables |
| `xref_` | Cross-reference tables |
| `bridge_` | Bridge tables |
| `feature_` | Feature store tables |
| `mart_` | Analytical mart tables |
| `ctl_` | Run control tables |
| `reject_` | Quarantine tables |

## Implementation Phases

| Phase | Status | Description |
|---|---|---|
| **Phase 0** | Done | PDR closure, 13-image decision, data model |
| **Phase 1** | Done | Source manifest, metadata ingestion, dim_image (12,736 rows) |
| **Phase 1A** | Done | Extract → parse → load → validate → observe pipeline |
| **Phase 2** | Done (synthetic) | Voter surrogates, batch/pairwise/category fact tables (100 synthetic voters) |
| **Phase 2A** | Done | Feature extraction (visual, CLIP, text) + clustering (k-means, HDBSCAN) |
| **Phase 2B** | Done | Full-scale: all thumbnails downloaded, features extracted, k=25 clustering complete |
| **Phase 3** | Done | Statistical modeling (Elo, Borda, Beta-Binomial, composite, reliability) |
| **Phase 4** | Done | Calendar optimization (5 methods, month/cover scoring, candidate generation) |
| **C4** | Done | Calendar rendering: targeted image download, 8.5x11 page layout, cover + 13 monthly pages, multi-page PDF assembly, `render-calendar` CLI |
| **C5** | Done | Review package: comparison scorecard, contact sheets, selection reports, layout validation, export assembly, `review-package` CLI |
| **S3–S4** | Done | Synthetic validation: bias detection, optimization validation |
| **Phase 5** | Not started | Learning and publication package |

## Documentation Structure

Design documents live in `docs/`. Once code exists, architecture and methodology docs should follow the numbered scheme from the PDR: `docs/00_project_overview.md` through `docs/15_methodology_for_publication.md`. Lessons learned go in `docs/lessons/` with structured entries (problem, why it matters, design choice, alternatives, what was learned).

## Privacy Constraints

- Never store raw voter IDs; use salted hashes
- Never attempt to identify voters
- Public reports: aggregate counts, image-level scores, cluster summaries, methodology — never voter-level rows
- Voter surrogates use identity confidence levels: exact, probable, weak, unknown
