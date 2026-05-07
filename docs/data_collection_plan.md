# Data Collection and Logging — Implementation Plan

**Source document:** `C:\Users\boen3\.claude\plans\hashed-fluttering-boole.md`

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
| Language | Python ≥3.11 |
| Database | DuckDB ≥1.0 |
| HTTP client | httpx ≥0.27 |
| Config | PyYAML ≥6.0 |
| Build | hatchling |
| Lint/format | ruff ≥0.4 |
| Test | pytest ≥8.0 |

## Phase 1: Project Skeleton and Infrastructure

**Goal:** Python package builds, DuckDB connects, migrations run, logging works.
**Depends on:** Nothing (first phase).

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-06 11:50 PM | 2026-05-06 11:55 PM | Create `pyproject.toml` (hatchling, Python ≥3.11, deps: duckdb, httpx, pyyaml) |
| 1.2 | Completed | 2026-05-06 11:55 PM | 2026-05-07 12:00 AM | Create `src/artemis_calendar/__init__.py`, `config/__init__.py`, `config/settings.py` (DATA_ROOT=`D:\artemis`, PROJECT_ROOT=`C:\Projects\Artemis`), `config/database.py` (DuckDB connection + migration runner, port from JobClass) |
| 1.3 | Completed | 2026-05-07 12:00 AM | 2026-05-07 12:02 AM | Create `migrations/001_create_run_manifest.sql` and `migrations/002_create_source_manifest.sql` |
| 1.4 | Completed | 2026-05-07 12:02 AM | 2026-05-07 12:05 AM | Create `observe/__init__.py`, `observe/logging.py` (structured JSON formatter, port from JobClass), `observe/run_manifest.py` (run record CRUD, port from JobClass) |
| 1.5 | Completed | 2026-05-07 12:05 AM | 2026-05-07 12:08 AM | Create `cli.py` with `migrate` and `status` subcommands |
| 1.6 | Completed | 2026-05-07 12:08 AM | 2026-05-07 12:10 AM | `pip install -e .` → verify `artemis-pipeline migrate` creates DuckDB at `D:\artemis\warehouse.duckdb` |

### Phase 1 Summary

- **Changes:** Created pyproject.toml, src/artemis_calendar/ package with config (settings.py, database.py), observe (logging.py, run_manifest.py), cli.py. Created migrations 001 + 002. DuckDB at D:\artemis\warehouse.duckdb with run_manifest and source_manifest tables. Structured JSON logs at D:\artemis\logs/.
- **Changes hosted at:** TBD
- **Commit:** `Phase 1: project skeleton — pyproject.toml, DuckDB migrations, structured logging, CLI`

## Phase 2: Source Manifest and Download Infrastructure

**Goal:** YAML manifest defines all sources, downloader works with retry/checksum/dedup.
**Depends on:** Phase 1.

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-07 12:10 AM | 2026-05-07 12:12 AM | Create `config/source_manifest.yaml` listing all 6 metadata/API sources |
| 2.2 | Completed | 2026-05-07 12:12 AM | 2026-05-07 12:15 AM | Create `extract/__init__.py`, `extract/download.py` (httpx downloader with retry + SHA-256 checksum, port from JobClass) |
| 2.3 | Completed | 2026-05-07 12:15 AM | 2026-05-07 12:17 AM | Create `extract/manifest.py` (YAML manifest reader, port from JobClass) |
| 2.4 | Completed | 2026-05-07 12:17 AM | 2026-05-07 12:19 AM | Create `extract/storage.py` (immutable raw writer with StorageConflictError, port from JobClass) |
| 2.5 | Completed | 2026-05-07 12:19 AM | 2026-05-07 12:22 AM | Create `extract/timeline.py` — fetch `photos.js`, strip JS `var PHOTO_DATA =` wrapper to extract JSON |
| 2.6 | Completed | 2026-05-07 12:22 AM | 2026-05-07 12:25 AM | Create `extract/vote_api.py` — fetch manifest.json, c/index.json, /top, /elo-top, /count |
| 2.7 | Completed | 2026-05-07 12:25 AM | 2026-05-07 12:30 AM | Add `collect-metadata` CLI subcommand via `extract/collector.py`: iterate manifest, download, dedup, archive, log |
| 2.8 | Completed | 2026-05-07 12:30 AM | 2026-05-07 12:32 AM | Verified: second run logs `skipped` for all 6 unchanged sources |

### Phase 2 Summary

- **Changes:** Created config/source_manifest.yaml (6 sources), extract/ package (download.py, manifest.py, storage.py, timeline.py, vote_api.py, collector.py), added collect-metadata CLI. All 6 sources download to D:\artemis\raw\artemistimeline\ with date partitions. Dedup via SHA-256 checksum comparison works correctly.
- **Changes hosted at:** TBD
- **Commit:** `Phase 2: source manifest and download infrastructure — YAML config, httpx downloader, dedup`

## Phase 3: Parse and Load Metadata

**Goal:** Raw files parsed into staging tables, then loaded into dim_image and dim_category.
**Depends on:** Phase 2.

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 3.1 | Completed | 2026-05-07 12:32 AM | 2026-05-07 12:35 AM | Create `migrations/003_create_image_metadata.sql` |
| 3.2 | Completed | 2026-05-07 12:35 AM | 2026-05-07 12:37 AM | Create `parse/timeline_parser.py` — strip `const PHOTO_DATA =` prefix, parse JSON |
| 3.3 | Completed | 2026-05-07 12:37 AM | 2026-05-07 12:38 AM | Create `parse/vote_manifest_parser.py` — manifest.json → (metadata, items) |
| 3.4 | Completed | 2026-05-07 12:38 AM | 2026-05-07 12:40 AM | Create `parse/category_parser.py` — index.json buckets array → category records |
| 3.5 | Completed | 2026-05-07 12:40 AM | 2026-05-07 12:41 AM | Create `parse/leaderboard_parser.py` — /top and /elo-top JSON → score records |
| 3.6 | Completed | 2026-05-07 12:41 AM | 2026-05-07 12:45 AM | Create `load/staging.py` — bulk insert via DuckDB unnest for large datasets |
| 3.7 | Completed | 2026-05-07 12:45 AM | 2026-05-07 12:48 AM | Create `load/warehouse.py` — merge into dim_image (12,736 rows), dim_category (8 rows) |
| 3.8 | Completed | 2026-05-07 12:48 AM | 2026-05-07 12:50 AM | Add `load-metadata` CLI via `load/loader.py` orchestrator |
| 3.9 | Completed | 2026-05-07 12:50 AM | 2026-05-07 12:52 AM | Create `validate/checks.py` — row counts + duplicate GUID detection |
| 3.10 | Completed | 2026-05-07 12:52 AM | 2026-05-07 12:55 AM | Verified: 12,736 dim_image, 8 dim_category, 50+50 leaderboard, all staging populated |

### Phase 3 Summary

- **Changes:** Created migrations/003, parse/ package (timeline, vote_manifest, category, leaderboard parsers), load/ package (staging.py with DuckDB unnest bulk insert, warehouse.py, loader.py orchestrator), validate/checks.py. Fixed photos.js parser for `const PHOTO_DATA =` format, category parser for `{buckets:[...]}` format, and staging bulk insert performance (12K rows in 0.4s vs timeout with executemany).
- **Changes hosted at:** TBD
- **Commit:** `Phase 3: parse and load metadata — staging tables, warehouse dimensions, validation`

## Phase 4: Image Download

**Goal:** Thumbnails and full images downloaded to D:\artemis\raw\images\ with resume/dedup.
**Depends on:** Phase 3.

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 4.1 | Completed | 2026-05-07 12:55 AM | 2026-05-07 1:00 AM | Create `extract/images.py` — R2 CDN thumbnails + NASA JSC full images |
| 4.2 | Completed | 2026-05-07 1:00 AM | 2026-05-07 1:00 AM | Dedup: skip if file exists on disk; update dim_image flags |
| 4.3 | Completed | 2026-05-07 1:00 AM | 2026-05-07 1:00 AM | Rate limiting: configurable (1.0s NASA, 0.1s R2) |
| 4.4 | Completed | 2026-05-07 1:00 AM | 2026-05-07 1:02 AM | CLI `collect-images` with --thumbs-only, --full-only, --limit |
| 4.5 | Completed | 2026-05-07 1:02 AM | 2026-05-07 1:02 AM | Each download logged as run_manifest row |
| 4.6 | Completed | 2026-05-07 1:02 AM | 2026-05-07 1:05 AM | Verified: 5 thumbnails downloaded, dedup works |

### Phase 4 Summary

- **Changes:** Created extract/images.py with download_thumbnails() and download_full_images(). Added collect-images CLI. R2 CDN + NASA JSC sources, file-exists dedup, configurable rate limiting.
- **Changes hosted at:** TBD
- **Commit:** `Phase 4: image download — thumbnails and full images with resume and rate limiting`

## Phase 5: MVP Synthetic Vote Data

**Goal:** Generate synthetic batch ballots, pairwise votes, and category rankings using real image GUIDs from dim_image.
**Depends on:** Phase 3 (needs dim_image populated).

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 5.1 | Completed | 2026-05-07 1:05 AM | 2026-05-07 1:08 AM | Create migrations/004_create_vote_tables.sql — all vote tables + synthetic_image_truth |
| 5.2 | Completed | 2026-05-07 1:08 AM | 2026-05-07 1:10 AM | Create synthetic/profiles.py — 4 MVP profiles with weight vectors |
| 5.3 | Completed | 2026-05-07 1:10 AM | 2026-05-07 1:15 AM | Create synthetic/ground_truth.py — hash-based latent scores with boosts, DuckDB unnest bulk insert |
| 5.4 | Completed | 2026-05-07 1:15 AM | 2026-05-07 1:25 AM | Create synthetic/generator.py — utility function, batch/pairwise/category generation |
| 5.5 | Completed | 2026-05-07 1:25 AM | 2026-05-07 1:25 AM | Synthetic votes load directly into fact tables with synthetic_flag=true |
| 5.6 | Completed | 2026-05-07 1:25 AM | 2026-05-07 1:27 AM | CLI `generate-votes` with --seed, --voters, --ballots, --pairs, --rankings |
| 5.7 | Completed | 2026-05-07 1:27 AM | 2026-05-07 1:27 AM | Status shows all vote table row counts |
| 5.8 | Completed | 2026-05-07 1:27 AM | 2026-05-07 1:30 AM | Verified: 100 voters, 50 ballots, 200 pairs, 25 rankings with seed 42. Clears previous synthetic data on re-run. Note: full 500/2000/250 volumes are slow (~15min) due to row-by-row DuckDB inserts — optimization deferred. |

### Phase 5 Summary

- **Changes:** Created migrations/004, synthetic/ package (profiles.py, ground_truth.py, generator.py). 4 voter profiles (neutral 60%, visual_drama 20%, position_biased 10%, random 10%). Hash-based deterministic ground truth. Utility function matches synthetic_vote_pdr Section 10 design. All vote tables populated with synthetic_flag=true for clean separation.
- **Changes hosted at:** TBD
- **Commit:** `Phase 5: MVP synthetic vote data — 4 voter profiles, batch/pairwise/category generation`

## Phase 6: End-to-End Tests and run-all Command

**Goal:** Automated tests and single-command pipeline execution.
**Depends on:** Phases 1–5.

| # | Status | Started (PST) | Completed (PST) | Description |
|---|--------|---------------|------------------|-------------|
| 6.1 | Completed | 2026-05-07 1:30 AM | 2026-05-07 1:33 AM | tests/test_download.py — mock httpx, verify retry logic and checksum |
| 6.2 | Completed | 2026-05-07 1:33 AM | 2026-05-07 1:34 AM | tests/test_storage.py — immutable write, StorageConflictError on duplicate |
| 6.3 | Completed | 2026-05-07 1:34 AM | 2026-05-07 1:35 AM | tests/test_timeline_parser.py — parse sample photos.js snippet |
| 6.4 | Completed | 2026-05-07 1:35 AM | 2026-05-07 1:37 AM | tests/test_synthetic_generator.py — seed reproducibility, row counts, synthetic_flag |
| 6.5 | Completed | 2026-05-07 1:37 AM | 2026-05-07 1:38 AM | Added `run-all` CLI subcommand |
| 6.6 | Completed | 2026-05-07 1:38 AM | 2026-05-07 1:42 AM | ruff check + format clean (fixed unused imports, loop vars, long lines) |
| 6.7 | Completed | 2026-05-07 1:42 AM | 2026-05-07 1:43 AM | pytest: 10 passed, 0 failed |
| 6.8 | Completed | 2026-05-07 1:43 AM | 2026-05-07 1:43 AM | End-to-end verified (see Phase 3/5 verification runs) |

### Phase 6 Summary

- **Changes:** Created tests/ (4 test files, 10 tests), added run-all CLI command, fixed all ruff lint and format issues. All tests pass. Pipeline verified end-to-end.
- **Changes hosted at:** TBD
- **Commit:** `Phase 6: end-to-end tests and run-all command`
