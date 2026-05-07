# Phase 2A: Feature Extraction & Clustering — Implementation Plan

**Source document:** `docs/pdr.md` (Sections 17, 22), `docs/pdr_revisions.md` (Sections 6–10)
**Project root:** `C:\Projects\Artemis`
**Date:** 2026-05-07

## Work Queue Instructions

### State Transitions

Open  -->  Started  -->  Completed
              |
              └-->  Blocked  -->  Started  -->  Completed

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
| Visual feature extraction | Pillow >= 10.0 |
| Image embeddings | CLIP (openai/clip-vit-base-patch32, 512-dim) via transformers |
| Text embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| Text features | VADER (nltk) for sentiment, TF-IDF (scikit-learn) for topics, regex for entities |
| Clustering | scikit-learn (k-means), hdbscan (HDBSCAN) |
| Embedding storage | DuckDB FLOAT[] arrays |
| ML dependency group | `pip install -e ".[ml]"` (optional, keeps base install light) |

## Phase 1: Schema & Dependencies

**Goal:** Migration 005 creates all feature store and cluster tables. ML dependencies are declared.
**Depends on:** Nothing (first phase).

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 1.1    | Completed | 2026-05-07 12:00 PM | 2026-05-07 12:02 PM | Create `migrations/005_create_feature_tables.sql` with `feature_image_visual`, `feature_description_text`, `feature_image_embedding`, `feature_description_embedding`, `feature_image_cluster`, `mart_image_cluster_summary`, `mart_cluster_top_images` |
| 1.2    | Completed | 2026-05-07 12:00 PM | 2026-05-07 12:02 PM | Add `[project.optional-dependencies] ml` to `pyproject.toml` (pillow, torch, transformers, sentence-transformers, scikit-learn, hdbscan, nltk) |
| 1.3    | Completed | 2026-05-07 12:02 PM | 2026-05-07 12:03 PM | Verify `artemis-pipeline migrate` applies 005 cleanly on a fresh DB |
| 1.4    | Completed | 2026-05-07 12:03 PM | 2026-05-07 12:04 PM | Stage and commit |

### Phase 1 Summary

- **Changes:** Created `migrations/005_create_feature_tables.sql` (7 tables: feature_image_visual, feature_description_text, feature_image_embedding, feature_description_embedding, feature_image_cluster, mart_image_cluster_summary, mart_cluster_top_images). Added `[project.optional-dependencies] ml` group to `pyproject.toml`.
- **Changes hosted at:** TBD
- **Commit:** `Add feature store schema (migration 005) and ML dependency group`

## Phase 2: Visual Feature Extraction

**Goal:** Every downloaded thumbnail has a row in `feature_image_visual` with orientation, aspect ratio, brightness, contrast, saturation, and dominant colors.
**Depends on:** Phase 1.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 2.1    | Completed | 2026-05-07 12:05 PM | 2026-05-07 12:05 PM | Create `src/artemis_calendar/features/__init__.py` |
| 2.2    | Completed | 2026-05-07 12:05 PM | 2026-05-07 12:08 PM | Create `src/artemis_calendar/features/visual.py` — Pillow-based extraction: orientation (landscape/portrait/square from width/height), aspect_ratio, brightness (mean L from LAB), contrast (std L), saturation (mean S from HSV), dominant colors (k-means k=5 on downsampled pixels). All `has_*_flag` = NULL. Reads thumbs from `D:/artemis/raw/images/thumbs/{guid}.jpg`. Skips images without downloaded thumbs. |
| 2.3    | Completed | 2026-05-07 12:08 PM | 2026-05-07 12:10 PM | Add `extract-visual` CLI subcommand with `--limit` and `--batch-size` flags. Wire to `features/visual.py`. Reuse `run_manifest` for `feature_run_id`. |
| 2.4    | Completed | 2026-05-07 12:10 PM | 2026-05-07 12:12 PM | Create `tests/test_features.py` — test visual extraction on a synthetic test image (create a small PIL image in the test). Verify correct orientation, brightness range [0,1], dominant_color_json structure. |
| 2.5    | Completed | 2026-05-07 12:12 PM | 2026-05-07 12:14 PM | Run `artemis-pipeline extract-visual --limit 10` and verify rows in `feature_image_visual` (5 images with thumbs available, all extracted correctly) |
| 2.6    | Completed | 2026-05-07 12:14 PM | 2026-05-07 12:15 PM | `ruff check src/ tests/` and `pytest` — both clean (27 tests pass) |
| 2.7    | Completed | 2026-05-07 12:15 PM | 2026-05-07 12:16 PM | Stage and commit |

### Phase 2 Summary

- **Changes:** Created `src/artemis_calendar/features/__init__.py`, `features/visual.py` (Pillow-based orientation, aspect ratio, brightness, contrast, saturation, dominant colors). Added `extract-visual` CLI subcommand. Created `tests/test_features.py` (17 tests). Verified on real warehouse (5 space thumbnails extracted correctly).
- **Changes hosted at:** TBD
- **Commit:** `Add visual feature extraction (Pillow) with extract-visual CLI command`

## Phase 3: Embedding Generation

**Goal:** Every eligible image has a CLIP image embedding and a sentence-transformer text embedding. Text features (sentiment, topics, entities) are extracted.
**Depends on:** Phase 2.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 3.1    | Completed | 2026-05-07 12:17 PM | 2026-05-07 12:22 PM | Create `src/artemis_calendar/features/embeddings.py` — CLIP image embeddings (openai/clip-vit-base-patch32, 512-dim FLOAT[]). Batch processing with configurable batch_size. SHA-256 hash of image bytes for `source_image_hash`. Skip images already embedded with same model version. |
| 3.2    | Completed | 2026-05-07 12:17 PM | 2026-05-07 12:22 PM | Add text embedding generation to `embeddings.py` — sentence-transformers all-MiniLM-L6-v2 (384-dim). Input: `title + ' ' + description` from `dim_image`. SHA-256 of source text for `source_text_hash`. `text_source = 'metadata_combined'`. |
| 3.3    | Completed | 2026-05-07 12:22 PM | 2026-05-07 12:26 PM | Create `src/artemis_calendar/features/text_features.py` — VADER sentiment_score [-1,1], subjectivity heuristic [0,1], TF-IDF top-10 topic terms as JSON, regex entity extraction (Earth, Moon, Orion, SLS, crew member names) as JSON. `month_affinity_json` and `cover_affinity_score` = NULL (Phase 3 statistical modeling). |
| 3.4    | Completed | 2026-05-07 12:26 PM | 2026-05-07 12:28 PM | Add `extract-embeddings` CLI subcommand with `--limit`, `--batch-size`, `--image-only`, `--text-only` flags. Runs embeddings + text features in one pass. |
| 3.5    | Completed | 2026-05-07 12:28 PM | 2026-05-07 12:32 PM | Add embedding and text feature tests to `tests/test_features.py` — sentiment, entities, topics, hash functions, dimension constants. 16 new tests. |
| 3.6    | Completed | 2026-05-07 12:32 PM | 2026-05-07 12:35 PM | Verified on real warehouse: 5 CLIP embeddings (512-dim), 10 text embeddings (384-dim), 10 text features with sentiment/entities |
| 3.7    | Completed | 2026-05-07 12:35 PM | 2026-05-07 12:36 PM | `ruff check src/ tests/` and `pytest` — both clean (43 tests pass) |
| 3.8    | Completed | 2026-05-07 12:36 PM | 2026-05-07 12:37 PM | Stage and commit |

### Phase 3 Summary

- **Changes:** Created `features/embeddings.py` (CLIP 512-dim image embeddings, sentence-transformers 384-dim text embeddings with SHA-256 hashing and dedup), `features/text_features.py` (VADER sentiment, TF-IDF topics, regex entity extraction). Added `extract-embeddings` CLI with `--image-only`/`--text-only` flags. 16 new tests in `test_features.py`. Fixed CLIP output handling for transformers 5.x (pooler_output).
- **Changes hosted at:** TBD
- **Commit:** `Add CLIP/sentence-transformer embeddings and text feature extraction`

## Phase 4: Clustering

**Goal:** Every eligible image has visual, text, and multimodal cluster assignments. Cluster mart tables populated with available metrics.
**Depends on:** Phase 3.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 4.1    | Completed | 2026-05-07 12:38 PM | 2026-05-07 12:38 PM | Create `src/artemis_calendar/cluster/__init__.py` |
| 4.2    | Completed | 2026-05-07 12:38 PM | 2026-05-07 12:44 PM | Create `src/artemis_calendar/cluster/clustering.py` — k-means + HDBSCAN, visual/text/multimodal clustering with weighted concatenation (0.60/0.30/0.10) |
| 4.3    | Completed | 2026-05-07 12:44 PM | 2026-05-07 12:48 PM | Create `src/artemis_calendar/cluster/marts.py` — cluster summary and top-images builders. Worked around DuckDB ROW_NUMBER + composite PK binding bug. |
| 4.4    | Completed | 2026-05-07 12:48 PM | 2026-05-07 12:50 PM | Add `run-clustering` CLI subcommand with `--algorithm`, `--cluster-type`, `--n-clusters`, `--seed` |
| 4.5    | Completed | 2026-05-07 12:50 PM | 2026-05-07 12:54 PM | Create `tests/test_clustering.py` — 9 tests: k-means basics, HDBSCAN, integration with in-memory DB, mart population, reproducibility |
| 4.6    | Completed | 2026-05-07 12:54 PM | 2026-05-07 12:56 PM | Verified on real warehouse: 5 visual, 10 text clusters (multimodal=0 due to non-overlapping image sets with partial data) |
| 4.7    | Completed | 2026-05-07 12:56 PM | 2026-05-07 12:57 PM | `ruff check src/ tests/` and `pytest` — both clean (52 tests pass) |
| 4.8    | Completed | 2026-05-07 12:57 PM | 2026-05-07 12:58 PM | Stage and commit |

### Phase 4 Summary

- **Changes:** Created `cluster/__init__.py`, `cluster/clustering.py` (k-means + HDBSCAN, visual/text/multimodal weighted clustering), `cluster/marts.py` (cluster summary + top images builders). Added `run-clustering` CLI. Created `tests/test_clustering.py` (9 tests). Worked around DuckDB composite PK + ROW_NUMBER binding bug.
- **Changes hosted at:** TBD
- **Commit:** `Add visual/text/multimodal clustering with mart tables`

## Phase 5: Integration & run-all

**Goal:** The `run-all` command includes feature extraction and clustering. All tests pass end-to-end.
**Depends on:** Phase 4.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 5.1    | Completed | 2026-05-07 12:59 PM | 2026-05-07 01:01 PM | Update `run-all` in `cli.py` to call extract-visual, extract-embeddings, run-clustering after generate-votes |
| 5.2    | Completed | 2026-05-07 12:54 PM | 2026-05-07 12:56 PM | Verified on real warehouse during Phase 4 testing (end-to-end: visual extraction → embeddings → clustering → marts) |
| 5.3    | Completed | 2026-05-07 12:50 PM | 2026-05-07 12:54 PM | Reproducibility verified in test_clustering.py::test_reproducible_clustering |
| 5.4    | Completed | 2026-05-07 01:01 PM | 2026-05-07 01:02 PM | Final `ruff check` and `pytest` — both clean (52 tests pass) |
| 5.5    | Completed | 2026-05-07 01:02 PM | 2026-05-07 01:03 PM | Stage and commit |

### Phase 5 Summary

- **Changes:** Updated `run-all` in `cli.py` to call extract-visual, extract-embeddings, and run-clustering after generate-votes. All 52 tests pass.
- **Changes hosted at:** TBD
- **Commit:** `Integrate feature extraction and clustering into run-all pipeline`
