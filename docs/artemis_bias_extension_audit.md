# Artemis Bias Extension Audit

**Purpose:** Audit of existing code paths relevant to the Phase 2 extension (biased voting blocks, vision tagging, clustering, static statistical reporting). Identifies reuse opportunities, gaps, and recommended integration approach for each layer.

**Date:** 2026-05-08

---

## 1. Synthetic Voter System (`src/artemis_calendar/synthetic/`)

### What exists

| File | Purpose |
|---|---|
| `profiles.py` | 4 voter profiles: neutral (60%), visual_drama (20%), position_biased (10%), random (10%). Each has weights for general_appeal, visual_drama, cover_value, position_bias_strength, randomness. |
| `generator.py` | `generate_synthetic_votes()` — creates voters via population share sampling, generates batch ballots (pick 5 of 50), pairwise votes, category rankings. Uses `_compute_utility()` with profile-weighted scoring. |
| `ground_truth.py` | `assign_ground_truth()` — assigns latent appeal/drama/cover scores to all vote-pool images using deterministic hash + heuristic boosts (timeline, enabled, showcase). |

### Extension points

- **Voter assignment:** Currently random profile sampling from `PROFILES` list by `population_share`. Extension needs block-based assignment where voters belong to a named block with explicit attribute-based preference rules.
- **Utility function:** Current `_compute_utility()` uses `general_appeal * w + visual_drama * w + cover_value * w + position_bias + noise`. Extension needs `attribute_match_score` based on image vision labels (earth, moon, etc.) which doesn't exist yet.
- **Run metadata:** Uses `synthetic_run_id` and `create_run_record()`. Extension adds `scenario_id`, `block_id` to the run model.

### Gap analysis

| Need | Status |
|---|---|
| Attribute-based preference rules (all_of, any_of, none_of) | **New** — no concept of image attributes in voting today |
| Block config from YAML | **New** — profiles are hardcoded in Python |
| Block-level voter assignment tracking | **New** — `dim_voter.synthetic_profile_code` exists but no `block_id` or `scenario_id` |
| Utility function with attribute matching | **Extend** — current utility is additive; add attribute_match_score term |
| Multiple scenarios per run | **New** — current system has one global synthetic run |

### Recommended approach

Create a new `synthetic/block_generator.py` alongside the existing `generator.py`. Reuse `_compute_utility()` pattern but add attribute-matching terms. Do not modify existing generator — it serves a different purpose (position-bias testing for S3 validation).

---

## 2. Feature Extraction (`src/artemis_calendar/features/`)

### What exists

| File | Purpose |
|---|---|
| `visual.py` | Pillow-based: orientation, aspect_ratio, brightness, contrast, saturation, dominant_colors. Parallel via ThreadPoolExecutor. |
| `embeddings.py` | CLIP (`openai/clip-vit-base-patch32`, 512-dim) image embeddings + sentence-transformers (`all-MiniLM-L6-v2`, 384-dim) text embeddings. Batch processing with skip-existing logic. |
| `text_features.py` | VADER sentiment, TF-IDF topics, entity extraction (editorial images only — 502 of 12,217). |

### Extension points

- **New embedding model:** Design calls for SigLIP instead of CLIP. Can coexist — `feature_image_embedding` has `embedding_model` and `embedding_model_version` columns. No schema change needed.
- **Vision tagging:** Entirely new capability. No existing structured attribute labels. The `feature_image_visual` table has `has_earth_flag`, `has_moon_flag`, `has_crew_flag`, `has_spacecraft_flag` columns — but these are all NULL today (never populated).
- **Attribute storage:** `feature_image_visual` has some boolean flag columns but no confidence scores. Design calls for a new `feature_image_attribute` table with per-attribute confidence scores and model metadata.

### Gap analysis

| Need | Status |
|---|---|
| SigLIP embeddings | **New model** — can use existing `feature_image_embedding` table with new `embedding_model_version` |
| Qwen2.5-VL structured labeling | **New** — no vision-language model integration |
| Per-attribute confidence scores | **New** — `feature_image_attribute` table needed |
| Derived attribute computation | **New** — e.g., earth_and_moon = earth AND moon |
| Review flagging for low confidence | **New** |

### Recommended approach

Create new `src/artemis_calendar/vision/` module for the VLM pipeline. Keep `features/` for low-level extraction (Pillow, CLIP). The `vision/` module is higher-level — it uses a VLM to produce structured labels, then stores them in the new attribute tables. SigLIP embeddings can go in either module; `vision/embeddings.py` keeps it co-located with the tagging pipeline.

---

## 3. Statistical Modeling (`src/artemis_calendar/models/`)

### What exists

| Component | Location | Output |
|---|---|---|
| Batch scores (selection rate, Wilson, Beta posterior) | `batch_scores.py` | Per-image dict |
| Elo scores | `pairwise_scores.py` | Per-image dict |
| Borda scores | `category_scores.py` | Per-image dict |
| Polarization | `batch_scores.py` | Per-image dict |
| Composite scoring | `composite.py` | Merges all into normalized composite with uncertainty and broad_appeal |
| Inter-rater reliability | `reliability.py` | Krippendorff's alpha per vote mode |
| Mart writers | `marts.py` | Writes to `mart_image_preference_score`, `mart_inter_rater_reliability`, backfills cluster marts |

### Extension points

- **Block-aware variants:** All scoring functions operate on the full vote population. Extension needs "score with block" vs "score without block" to compute score deltas and rank movement.
- **Attribute lift:** New calculation — per-block selection rate / global rate for each attribute. Not a modification of existing scoring.
- **Cluster lift:** Similar to attribute lift but per cluster. Existing `detect_cluster_bias()` in `validate/bias_detection.py` computes lift ratios already — can be generalized.

### Gap analysis

| Need | Status |
|---|---|
| Per-block selection rate | **New** |
| Attribute lift (block × attribute) | **New** |
| Cluster lift (block × cluster) | **Adapt** — `detect_cluster_bias()` pattern exists |
| Block similarity (Jaccard, cosine) | **New** |
| Score impact (with/without block) | **New** — requires re-running scoring pipeline with voter exclusion |
| Calendar impact | **New** — requires re-running optimization with voter exclusion |

### Recommended approach

Add block-aware statistics as a separate module (`models/block_stats.py` or similar). Don't modify existing scoring pipeline — it computes population-level scores. Block analysis is a comparison layer on top.

---

## 4. Bias Detection (`src/artemis_calendar/validate/`)

### What exists

| Function | What it does |
|---|---|
| `detect_position_bias()` | Chi-squared test on batch position thirds vs selection. Detects if early positions are over-selected. |
| `detect_cluster_bias()` | Chi-squared goodness-of-fit: observed cluster selection vs expected proportional. Computes lift ratios, returns top 3 over-selected clusters. |
| `segment_voters()` | Jaccard agreement between each voter's selections and population top-50. Groups by `synthetic_profile_code`. |
| `compare_scores_to_truth()` | Spearman rank correlation between computed composite and planted ground truth. |
| `reliability_under_bias()` | Krippendorff's alpha with/without biased profiles. |
| `run_bias_detection()` | Orchestrator. Writes to `mart_bias_detection`. |

### Extension points

- **Block-level detection:** `detect_cluster_bias()` already computes lift. Extend to accept a block_id filter for per-block analysis.
- **Voter segmentation by block:** `segment_voters()` groups by profile_code. Extend to group by block_id.
- **Score-truth comparison per block:** `compare_scores_to_truth()` can be parameterized to exclude specific blocks.

### Gap analysis

| Need | Status |
|---|---|
| Per-block bias detection (intended vs detected) | **New** — orchestration layer |
| Detection strength/confidence/status | **New** — classification of detected/partially_detected/not_detected |
| Block-level evidence (primary/secondary) | **New** |
| Multi-block comparison | **New** |

### Recommended approach

Add `validate/block_bias_detection.py` that wraps existing primitives (`detect_cluster_bias`, `segment_voters`) with block-level filtering. The orchestrator produces detection results per block and a scenario-level summary.

---

## 5. Clustering (`src/artemis_calendar/cluster/`)

### What exists

| File | Purpose |
|---|---|
| `clustering.py` | K-Means + HDBSCAN on CLIP visual, sentence-transformer text, or weighted multimodal embeddings. Writes to `feature_image_cluster`. |
| `marts.py` | `build_cluster_summary()` and `build_cluster_top_images()` — populate `mart_image_cluster_summary` and `mart_cluster_top_images`. |

### Extension points

- **SigLIP embeddings:** `_load_embeddings()` accepts any `embedding_model_version`. Adding SigLIP-based clustering is a config change, not a code change.
- **Vision-enhanced clustering:** After vision tagging, attribute labels can be concatenated as features for clustering. Requires extending the multimodal concatenation in `run_clustering()`.
- **Cluster labeling:** Design calls for labels generated from dominant attributes + representative captions. Currently `cluster_label` in `feature_image_cluster` is NULL — auto-labels not implemented.

### Gap analysis

| Need | Status |
|---|---|
| SigLIP-based clustering | **Config change** — pass different model_version |
| Attribute-enhanced multimodal | **Extend** — add attribute features to concatenation |
| Auto-generated cluster labels | **New** — from dominant attributes + captions |
| Cluster review output (JSON/MD) | **New** |
| Cluster-level voting block lift summary | **New** |

### Recommended approach

The design's `dim_image_cluster_run` / `dim_image_cluster` / `bridge_image_cluster_assignment` tables are more normalized than the current flat `feature_image_cluster`. For Phase 4, decide whether to:
- (a) Add the new tables alongside existing ones (recommended — avoids breaking working pipeline)
- (b) Migrate to the new schema (risky — breaks 168 passing tests)

Cluster labeling goes in the new `vision/cluster_labels.py` since it depends on vision attributes.

---

## 6. Static Site (`_site_new/`)

### What exists

| Asset | Purpose |
|---|---|
| `index.html` | SPA shell with fetch-intercept layer that maps API calls to static JSON files. Hash routing: #/images, #/candidates, #/clusters, #/stats, #/selection, #/lessons. |
| `api/stats.json` | Reliability, bias (empty `{}`), score distribution, vote counts, image count. |
| `api/clusters/index.json` + `api/clusters/0.json`…`24.json` | Cluster metadata and member images. |
| `api/candidates/index.json` + per-method JSONs | Candidate comparison data. |
| `api/images/all.json` + `api/images/details.json` | Full image catalog (client-side filter/sort/paginate). |
| `static/js/pages/stats.js` | Stats page rendering — currently shows reliability, score distribution chart, vote counts. |
| `static/css/` | Atlas design tokens + system styles + app styles. |

### Extension points

- **Fetch intercept:** New routes (e.g., `/api/voting-block-summary`) need to be added to the fetch intercept in `index.html`.
- **Stats page:** `stats.js` needs new sections for voting bias, vision labels, clusters, lift charts.
- **JSON files:** New static JSON files need to be generated and placed in `api/`.

### Gap analysis

| Need | Status |
|---|---|
| `api/vision-summary.json` | **New** |
| `api/voting-block-summary.json` | **New** |
| `api/voting-block-attribute-lift.json` | **New** |
| `api/voting-block-cluster-lift.json` | **New** |
| `api/voting-block-score-impact.json` | **New** |
| `api/voting-block-calendar-impact.json` | **New** |
| Stats page: Voting Bias Analysis section | **New** |
| Stats page: Vision Label Summary section | **New** |
| Stats page: Attribute/Cluster Lift charts | **New** |
| Stats page: Block Similarity matrix | **New** |
| Stats page: Score Impact section | **New** |
| Stats page: Calendar Impact section | **New** |
| Static JSON export CLI command | **New** |

### Recommended approach

Add a `src/artemis_calendar/static/` module with an `exporter.py` that queries mart tables and writes sanitized JSON to `_site_new/api/`. Add fetch intercepts in `index.html` for the new routes. Extend `stats.js` with new sections — keep the same Atlas design system patterns.

---

## 7. CLI Structure (`src/artemis_calendar/cli.py`)

### What exists

17 subcommands registered via `argparse.add_subparsers()`:
- Pipeline: `migrate`, `status`, `collect-metadata`, `load-metadata`, `collect-images`
- Synthetic: `generate-votes`
- Features: `extract-visual`, `extract-embeddings`
- Clustering: `run-clustering`
- Modeling: `compute-scores`
- Optimization: `optimize`
- Rendering: `render-calendar`
- Review: `review-package`
- Validation: `validate-bias`, `validate-calendar`
- Web: `serve`
- Combined: `run-all`

### CLI registration pattern

All commands follow: `cmd_xyz(args)` function + subparser definition + registration in `commands` dict.

### New commands needed

| Command | Purpose |
|---|---|
| `vision tag-images` | Run Qwen2.5-VL tagging |
| `vision embed-images` | Run SigLIP embedding |
| `vision cluster-images` | Run vision-enhanced clustering |
| `vision summarize-clusters` | Generate cluster labels |
| `vision export-review` | Export cluster review |
| `votes generate-blocks` | Generate biased voting blocks |
| `votes validate-block-config` | Validate YAML config |
| `votes summarize-run` | Summarize voting block run |
| `stats compute-block-analysis` | Block-aware statistics |
| `stats compute-calendar-impact` | Calendar impact analysis |
| `stats export-static-json` | Export to static JSON |
| `static build` | Full static site build |

### Recommended approach

The design calls for hierarchical commands (`vision tag-images`, `votes generate-blocks`). Current CLI uses flat subcommands. Two options:
- (a) Add as flat commands with hyphens: `vision-tag-images`, `votes-generate-blocks` (consistent with existing pattern)
- (b) Use argparse sub-subparsers for hierarchical commands (more complex, better UX)

**Recommend (a)** for consistency. The number of commands is manageable and the flat pattern is proven.

---

## 8. Database Schema Summary

### Existing tables relevant to extension

| Table | Relevance |
|---|---|
| `dim_voter` | Has `synthetic_profile_code` — needs `block_id`, `scenario_id` |
| `feature_image_visual` | Has unused `has_earth_flag`, `has_moon_flag`, `has_crew_flag`, `has_spacecraft_flag` columns |
| `feature_image_embedding` | Supports multiple models via `embedding_model_version` |
| `feature_image_cluster` | Flat structure — design calls for more normalized approach |
| `synthetic_image_truth` | Ground truth for validation — may need extension for attribute-aware truth |
| `mart_bias_detection` | Population-level detection — needs block-level variant |

### New tables needed

| Table | Purpose |
|---|---|
| `dim_image_attribute` | Attribute vocabulary (earth, moon, sun, etc.) |
| `feature_image_attribute` | Per-image attribute confidence scores |
| `dim_voting_scenario` | Voting scenario metadata |
| `dim_voting_block` | Block definitions per scenario |
| `voting_block_rule` | Preference rules per block |
| `synthetic_voter_block_assignment` | Voter-to-block mapping |
| `mart_voting_block_summary` | Per-block aggregate stats |
| `mart_voting_block_attribute_lift` | Attribute lift per block |
| `mart_voting_block_cluster_lift` | Cluster lift per block |
| `mart_voting_block_image_lift` | Image-level lift per block |
| `mart_voting_block_similarity` | Block-pair similarity |
| `mart_voting_block_score_impact` | Score with/without block |
| `mart_voting_block_calendar_impact` | Calendar changes per scenario |

### New migration needed

`009_create_vision_and_voting_block_tables.sql` — all new tables above.

---

## 9. Dependency Inventory

### Current dependencies (`pyproject.toml`)

| Group | Packages |
|---|---|
| Core | duckdb, httpx, pyyaml |
| ML | pillow, torch, transformers, sentence-transformers, scikit-learn, hdbscan |
| Web | fastapi[standard] |
| Dev | pytest, ruff |

### New dependencies needed

| Package | Purpose | Group |
|---|---|---|
| `transformers>=4.40` | Already present for CLIP — Qwen2.5-VL uses same library | ml |
| `qwen-vl-utils` | Qwen2.5-VL image processing utilities | ml (new) |
| `open_clip_torch` or SigLIP via `transformers` | SigLIP embeddings | ml (may already be covered) |
| `scipy` | Already used in `validate/bias_detection.py` — needed for chi-squared, etc. | Implicit dep of scikit-learn |

Most dependencies are already present. The main new dependency is `qwen-vl-utils` for the Qwen2.5-VL model.

---

## 10. Summary and Recommendations

### Key decisions for implementation

1. **New `vision/` module** — separate from `features/` for VLM-level analysis
2. **New `synthetic/block_generator.py`** — alongside existing generator, not replacing it
3. **Flat CLI commands** — consistent with existing `artemis-pipeline` pattern
4. **New migration `009`** — all schema additions in one migration
5. **Additive schema** — new tables alongside existing ones, no breaking changes
6. **Static export module** — `src/artemis_calendar/static/exporter.py` for JSON generation
7. **Extend `_site_new/`** — new JSON files in `api/`, new sections in `stats.js`

### Risk areas

- **Qwen2.5-VL resource requirements:** 7B model needs ~16GB VRAM. User's machine capability is unknown. Plan for 3B fallback.
- **SigLIP vs CLIP:** Existing pipeline uses CLIP. Switching to SigLIP may change cluster boundaries. Run both and compare.
- **12,217 images × vision model:** Batch processing at ~1-2 sec/image = 3-7 hours. Need progress tracking, resume capability.
- **Vote utility function tuning:** The attribute_match_score weighting needs careful calibration to produce detectable but not overwhelming bias.
