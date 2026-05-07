# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Artemis is a data science and data engineering platform for selecting a high-quality **Artemis II 13-month calendar image collection** (December 2026 through December 2027). The core problem is **collection optimization, not top-N ranking** — selecting 13 images that work together as a calendar (1 cover + 12 monthly pages), balancing voter preference, visual diversity, mission coverage, month suitability, and redundancy control.

The project sources imagery and voting data from ArtemisTimeline.com, which hosts ~12,000 Artemis II mission photos with three voting modes: random-batch (50 shown, pick 5), head-to-head Elo, and category top-3 ranking.

## Project Status

**Through Phase 2A.** Data pipeline, synthetic votes, feature extraction, and clustering are implemented.

### What exists

| Layer | Status |
|---|---|
| Extract / parse / load pipeline | Working — metadata, images, vote manifest |
| Warehouse (`D:/artemis/warehouse.duckdb`) | `dim_image` 12,736 rows, `dim_category` 8, synthetic voters/votes populated |
| Feature extraction | `features/visual.py` (Pillow), `features/embeddings.py` (CLIP 512-dim + sentence-transformers 384-dim), `features/text_features.py` (VADER, TF-IDF, entities) |
| Clustering | `cluster/clustering.py` (k-means, HDBSCAN), `cluster/marts.py` (summary + top images) |
| CLI commands | `migrate`, `status`, `collect-metadata`, `load-metadata`, `collect-images`, `generate-votes`, `extract-visual`, `extract-embeddings`, `run-clustering`, `run-all` |
| Tests | 52 passing (pytest), ruff clean |

### Data gap

Only **5 of 12,217** vote-pool images have downloaded thumbnails. Feature extraction and clustering ran on this tiny sample. The next step is downloading all thumbnails from the R2 CDN before re-running feature extraction at scale.

### Design documents

- `docs/pdr.md` — Physical Design Review: full data model, pipeline architecture, warehouse schema, statistical methods, acceptance criteria
- `docs/pdr_revisions.md` — Addenda: archive/refresh pipeline, clustering design, month/cover scoring, lessons-learned registry, Pipeline Explorer
- `docs/synthetic_vote_pdr.md` — Synthetic voter data generator design for bias detection testing
- `docs/feature_extraction_plan.md` — Phase 2A plan (all 5 phases completed)

## Architecture

The project follows a **JobClass-style layered warehouse pattern** (modeled after `github.com/bonjohen/jobclass`):

**Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports**

Package layout under `src/artemis_calendar/`:

| Module | Status | Purpose |
|---|---|---|
| `config/` | Exists | Source manifests, settings, paths, database connection |
| `extract/` | Exists | Download source pages, manifests, images, vote data |
| `parse/` | Exists | Source-specific parsers (timeline, category, leaderboard, vote manifest) |
| `load/` | Exists | Staging and warehouse loaders |
| `validate/` | Partial | `checks.py` exists; drift/referential/semantic checks not yet wired |
| `observe/` | Exists | Run manifests, structured JSON logging |
| `features/` | Exists | Image/text embeddings, sentiment, visual features |
| `cluster/` | Exists | Visual, text, and multimodal clustering + mart builders |
| `synthetic/` | Exists | Voter profiles, ground truth, vote generator |
| `models/` | Not started | Preference scoring (Elo, BTL, Bayesian), reliability models |
| `optimize/` | Not started | Calendar slate generation and month assignment |
| `marts/` | Not started | Analytical outputs (beyond cluster marts) |
| `reports/` | Not started | Review packages |

## Source Sites and Download Rules

Three upstream sources serve image data. All permit automated access but require respectful rate limiting.

### R2 CDN — Thumbnails (primary for feature extraction)

- **Base URL:** `https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/{guid}.jpg`
- **robots.txt:** No robots.txt (404). Cloudflare R2 public bucket.
- **Rate limit headers:** None returned. No `Retry-After`, no `X-RateLimit-*`.
- **Observed behavior:** Cloudflare-fronted, SEA edge. No throttling detected at 10 req/s in small tests.
- **Our rate limit:** `RATE_LIMIT_R2_CDN = 0.1s` (10/sec) in `config/settings.py`. This is aggressive for 12K images — consider raising to 0.2–0.5s for sustained bulk download to avoid triggering Cloudflare bot detection.
- **Thumbnail size:** ~20 KB avg. Total for 12,217 images: ~234 MB.
- **Estimated time at 0.1s:** ~20 min. At 0.25s: ~50 min.

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

### Download Strategy

1. **Thumbnails first.** Download all 12,217 thumbnails from R2 CDN. This unblocks visual feature extraction, CLIP embeddings, and clustering at full scale.
2. **Full images deferred.** Only needed for Phase C4 (page rendering). ~7 GB download at 1 req/s = ~3.4 hours from NASA. Not urgent.
3. **Use `--limit` for incremental runs.** Download in batches (e.g., `--limit 1000`) to monitor progress and catch failures early.
4. **Existing code handles resume.** `collect-images` skips images already on disk and updates `thumb_downloaded` flags. Safe to re-run.

## Key Design Decisions

- **Immutable raw archive**: Every source snapshot preserved with content hash, never modified after capture
- **Natural grain preservation**: Vote events stored at their native grain (batch ballots, pairwise comparisons, category rankings) — not collapsed into single scores prematurely
- **Surrogate voter keys**: Anonymous voter continuity via `voter_sk` + hashed source IDs; no PII storage
- **Dual operating modes**: Full raw-vote mode (if data is provided) and aggregate-only fallback mode
- **Calendar as portfolio optimization**: Multi-objective function balancing preference, diversity, month fit, cover fit, mission coverage, minus redundancy/uncertainty penalties
- **13-image calendar**: Cover image must be one of the 13 monthly images, selected by composite popularity + cover suitability score

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
| **Thumbnail download** | **Next** | Download 12,212 remaining thumbnails, then re-run feature extraction at scale |
| **Phase 3** | Not started | Statistical modeling (Elo, BTL, Bayesian scores, reliability) |
| **Phase 4** | Not started | Calendar optimization (objective function, month/cover scoring, candidate generation) |
| **Phase 5** | Not started | Learning and publication package |
| **C1–C5** | Not started | Calendar rendering: selection, month assignment, cover, 8.5x11 PDF/PNG, review |
| **S3–S4** | Not started | Synthetic validation: bias detection, optimization validation |

## Documentation Structure

Design documents live in `docs/`. Once code exists, architecture and methodology docs should follow the numbered scheme from the PDR: `docs/00_project_overview.md` through `docs/15_methodology_for_publication.md`. Lessons learned go in `docs/lessons/` with structured entries (problem, why it matters, design choice, alternatives, what was learned).

## Privacy Constraints

- Never store raw voter IDs; use salted hashes
- Never attempt to identify voters
- Public reports: aggregate counts, image-level scores, cluster summaries, methodology — never voter-level rows
- Voter surrogates use identity confidence levels: exact, probable, weak, unknown
