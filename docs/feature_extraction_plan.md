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
| 1.1    | Open   |               |                  | Create `migrations/005_create_feature_tables.sql` with `feature_image_visual`, `feature_description_text`, `feature_image_embedding`, `feature_description_embedding`, `feature_image_cluster`, `mart_image_cluster_summary`, `mart_cluster_top_images` |
| 1.2    | Open   |               |                  | Add `[project.optional-dependencies] ml` to `pyproject.toml` (pillow, torch, transformers, sentence-transformers, scikit-learn, hdbscan, nltk) |
| 1.3    | Open   |               |                  | Verify `artemis-pipeline migrate` applies 005 cleanly on a fresh DB |
| 1.4    | Open   |               |                  | Stage and commit |

### Phase 1 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `Add feature store schema (migration 005) and ML dependency group`

## Phase 2: Visual Feature Extraction

**Goal:** Every downloaded thumbnail has a row in `feature_image_visual` with orientation, aspect ratio, brightness, contrast, saturation, and dominant colors.
**Depends on:** Phase 1.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 2.1    | Open   |               |                  | Create `src/artemis_calendar/features/__init__.py` |
| 2.2    | Open   |               |                  | Create `src/artemis_calendar/features/visual.py` — Pillow-based extraction: orientation (landscape/portrait/square from width/height), aspect_ratio, brightness (mean L from LAB), contrast (std L), saturation (mean S from HSV), dominant colors (k-means k=5 on downsampled pixels). All `has_*_flag` = NULL. Reads thumbs from `D:/artemis/raw/images/thumbs/{guid}.jpg`. Skips images without downloaded thumbs. |
| 2.3    | Open   |               |                  | Add `extract-visual` CLI subcommand with `--limit` and `--batch-size` flags. Wire to `features/visual.py`. Reuse `run_manifest` for `feature_run_id`. |
| 2.4    | Open   |               |                  | Create `tests/test_features.py` — test visual extraction on a synthetic test image (create a small PIL image in the test). Verify correct orientation, brightness range [0,1], dominant_color_json structure. |
| 2.5    | Open   |               |                  | Run `artemis-pipeline extract-visual --limit 10` and verify 10 rows in `feature_image_visual` |
| 2.6    | Open   |               |                  | `ruff check src/ tests/` and `pytest` — both clean |
| 2.7    | Open   |               |                  | Stage and commit |

### Phase 2 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `Add visual feature extraction (Pillow) with extract-visual CLI command`

## Phase 3: Embedding Generation

**Goal:** Every eligible image has a CLIP image embedding and a sentence-transformer text embedding. Text features (sentiment, topics, entities) are extracted.
**Depends on:** Phase 2.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 3.1    | Open   |               |                  | Create `src/artemis_calendar/features/embeddings.py` — CLIP image embeddings (openai/clip-vit-base-patch32, 512-dim FLOAT[]). Batch processing with configurable batch_size. SHA-256 hash of image bytes for `source_image_hash`. Skip images already embedded with same model version. |
| 3.2    | Open   |               |                  | Add text embedding generation to `embeddings.py` — sentence-transformers all-MiniLM-L6-v2 (384-dim). Input: `title + ' ' + description` from `dim_image`. SHA-256 of source text for `source_text_hash`. `text_source = 'metadata_combined'`. |
| 3.3    | Open   |               |                  | Create `src/artemis_calendar/features/text_features.py` — VADER sentiment_score [-1,1], subjectivity heuristic [0,1], TF-IDF top-10 topic terms as JSON, regex entity extraction (Earth, Moon, Orion, SLS, crew member names) as JSON. `month_affinity_json` and `cover_affinity_score` = NULL (Phase 3 statistical modeling). |
| 3.4    | Open   |               |                  | Add `extract-embeddings` CLI subcommand with `--limit`, `--batch-size`, `--image-only`, `--text-only` flags. Runs embeddings + text features in one pass. |
| 3.5    | Open   |               |                  | Add embedding and text feature tests to `tests/test_features.py` — mock CLIP/sentence-transformer models for unit tests (don't require GPU). Verify FLOAT[] dimensions, hash computation, text feature JSON structure. |
| 3.6    | Open   |               |                  | Run `artemis-pipeline extract-embeddings --limit 10` and verify rows in all three tables |
| 3.7    | Open   |               |                  | `ruff check src/ tests/` and `pytest` — both clean |
| 3.8    | Open   |               |                  | Stage and commit |

### Phase 3 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `Add CLIP/sentence-transformer embeddings and text feature extraction`

## Phase 4: Clustering

**Goal:** Every eligible image has visual, text, and multimodal cluster assignments. Cluster mart tables populated with available metrics.
**Depends on:** Phase 3.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 4.1    | Open   |               |                  | Create `src/artemis_calendar/cluster/__init__.py` |
| 4.2    | Open   |               |                  | Create `src/artemis_calendar/cluster/clustering.py` — load embeddings from DuckDB as numpy arrays. Implement k-means (scikit-learn) and HDBSCAN. Visual clustering on CLIP vectors. Text clustering on sentence-transformer vectors. Multimodal: L2-normalize each vector, concatenate with weights (visual 0.60, text 0.30, metadata features 0.10), then cluster. Write `feature_image_cluster` with cluster_run_id, distances. |
| 4.3    | Open   |               |                  | Create `src/artemis_calendar/cluster/marts.py` — SQL-based builders. `mart_image_cluster_summary`: image_count, top_image_sk (min distance_to_centroid), mean_sentiment_score from feature_description_text. Score columns (preference, elo, borda) = NULL. `mart_cluster_top_images`: rank by distance_to_centroid within cluster, score columns NULL. |
| 4.4    | Open   |               |                  | Add `run-clustering` CLI subcommand with `--algorithm` (kmeans|hdbscan), `--cluster-type` (visual|text|multimodal|all), `--n-clusters` (default 25), `--seed`. |
| 4.5    | Open   |               |                  | Create `tests/test_clustering.py` — generate small random embedding matrices, verify cluster assignments are complete (every image assigned), reproducible (same seed = same result), and mart tables populated. |
| 4.6    | Open   |               |                  | Run full sequence: `extract-visual`, `extract-embeddings --limit 50`, `run-clustering --cluster-type all` and verify end-to-end |
| 4.7    | Open   |               |                  | `ruff check src/ tests/` and `pytest` — both clean |
| 4.8    | Open   |               |                  | Stage and commit |

### Phase 4 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `Add visual/text/multimodal clustering with mart tables`

## Phase 5: Integration & run-all

**Goal:** The `run-all` command includes feature extraction and clustering. All tests pass end-to-end.
**Depends on:** Phase 4.

| Task   | Status | Started (PST) | Completed (PST) | Description |
|--------|--------|---------------|------------------|-------------|
| 5.1    | Open   |               |                  | Update `run-all` in `cli.py` to call extract-visual, extract-embeddings, run-clustering after generate-votes |
| 5.2    | Open   |               |                  | End-to-end test: `artemis-pipeline run-all` on a fresh database with `--limit 20` for images |
| 5.3    | Open   |               |                  | Verify reproducibility: run clustering twice with same seed, compare cluster assignments |
| 5.4    | Open   |               |                  | Final `ruff check` and `pytest` |
| 5.5    | Open   |               |                  | Stage and commit |

### Phase 5 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `Integrate feature extraction and clustering into run-all pipeline`
