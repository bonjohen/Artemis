# Biased Voting Blocks, Vision Tagging, and Static Reporting — Implementation Plan

**Source document:** `docs/phase2design.md`

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
| Vision model | Qwen2.5-VL 7B (structured labels, captions, confidence scores) |
| Embedding model | SigLIP (image embeddings for clustering) |
| Clustering | HDBSCAN (natural discovery) + K-Means (fixed-k experiments) |
| Config format | YAML (voting block definitions, attribute vocabulary) |
| Validation | Pydantic v2 (config schemas, API models) |
| Static site | `_site_new/` — client-side JS SPA, static JSON in `api/` |
| Database | DuckDB (`D:/artemis/warehouse.duckdb`) |
| Optional vision | Florence-2 (secondary captioning), Grounding DINO / OWLv2 (object detection) |

---

## Phase 1: Audit and Alignment

**Goal:** Documented audit of existing code paths relevant to this extension — vote generation, synthetic voters, image features, statistics, bias detection, static JSON, stats page, CLI structure. No code changes.
**Depends on:** Nothing (first phase).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/synthetic/` — document voter profiles, vote generation, run metadata, and extension points |
| 1.2 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/features/` — document visual features, CLIP embeddings, text features, and how to add new feature extractors |
| 1.3 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/models/` — document Elo, Borda, Beta-Binomial, composite scoring, and where block-aware variants slot in |
| 1.4 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/validate/` — document `bias_detection.py`, `calendar_validation.py`, and extension points for block-level bias |
| 1.5 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/cluster/` — document clustering pipeline, mart builders, and how vision-enhanced clusters integrate |
| 1.6 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `_site_new/` — document static JSON schema (`api/`), front-end pages, stats rendering, and where new sections go |
| 1.7 | Completed | 2026-05-08 08:00 PM | 2026-05-08 08:15 PM | Audit `src/artemis_calendar/cli.py` — document existing subcommands and where new vision/votes/stats commands register |
| 1.8 | Completed | 2026-05-08 08:15 PM | 2026-05-08 08:25 PM | Write `docs/artemis_bias_extension_audit.md` — consolidated findings, gaps, reuse inventory, recommended approach for each layer |
| 1.9 | Completed | 2026-05-08 08:25 PM | 2026-05-08 08:26 PM | Stage and commit: `docs: audit existing code paths for bias extension` |

### Phase 1 Summary

- **Changes:** Created `docs/artemis_bias_extension_audit.md` — 10-section audit covering synthetic voters, features, models, validation, clustering, static site, CLI, database schema, dependencies, and recommendations. Documented all extension points, gaps, and integration approach for each layer.
- **Changes hosted at:** `docs/artemis_bias_extension_audit.md`
- **Commit:** `docs: audit existing code paths for bias extension`

---

## Phase 2: Attribute Vocabulary and Data Model

**Goal:** Controlled image-attribute vocabulary exists in config YAML and warehouse tables. Derived attribute rules are implemented. No vision model yet — just the schema and seed data.
**Depends on:** Phase 1.

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-08 08:28 PM | 2026-05-08 08:32 PM | Create `config/image_attributes.yaml` — 22 base attributes + 4 derived rules + confidence thresholds |
| 2.2 | Completed | 2026-05-08 08:28 PM | 2026-05-08 08:35 PM | Create `src/artemis_calendar/vision/__init__.py` and `vision/attributes.py` — dataclass models, YAML loading, derived label computation |
| 2.3 | Completed | 2026-05-08 08:28 PM | 2026-05-08 08:35 PM | Add `dim_image_attribute` + `feature_image_attribute` + all voting block tables in `migrations/009_create_vision_and_voting_block_tables.sql` |
| 2.4 | Completed | 2026-05-08 08:28 PM | 2026-05-08 08:35 PM | `feature_image_attribute` includes `classification` column (accepted/tentative/rejected) in addition to raw confidence score |
| 2.5 | Completed | 2026-05-08 08:35 PM | 2026-05-08 08:38 PM | Create `vision/loader.py` — `seed_attribute_vocabulary()` upserts dim_image_attribute, `write_image_attributes()` stores per-image scores + derived labels |
| 2.6 | Completed | 2026-05-08 08:28 PM | 2026-05-08 08:35 PM | Used dataclasses (Thresholds, BaseAttribute, DerivedRule, DerivedAttribute, AttributeVocabulary) — lighter than Pydantic for config-only validation |
| 2.7 | Completed | 2026-05-08 08:38 PM | 2026-05-08 08:42 PM | Added `tests/test_vision_attributes.py` — 17 tests: loading, derived labels, confidence thresholds, DB seed, DB write, edge cases |
| 2.8 | Completed | 2026-05-08 08:42 PM | 2026-05-08 08:43 PM | 185 tests pass, ruff clean |

### Phase 2 Summary

- **Changes:** Created `config/image_attributes.yaml` (22 base + 4 derived attributes), `src/artemis_calendar/vision/` module (`__init__.py`, `attributes.py`, `loader.py`), `migrations/009_create_vision_and_voting_block_tables.sql` (13 new tables for attributes, voting blocks, and block-level marts), `tests/test_vision_attributes.py` (17 tests). 185 tests pass, ruff clean.
- **Changes hosted at:** `src/artemis_calendar/vision/`, `config/image_attributes.yaml`, `migrations/009_*`
- **Commit:** `feat(vision): add attribute vocabulary schema, config, and warehouse tables`

---

## Phase 3: Local Vision Tagging

**Goal:** `artemis vision tag-images` CLI command runs Qwen2.5-VL locally, produces structured JSON labels with confidence scores per image, stores results in `feature_image_attribute`, flags low-confidence images for review.
**Depends on:** Phase 2.

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 3.1 | Completed | 2026-05-08 08:45 PM | 2026-05-08 08:55 PM | Create `vision/tagger.py` — VisionTagger (Qwen2.5-VL) + MockTagger for testing, structured prompt, JSON parsing |
| 3.2 | Completed | 2026-05-08 08:45 PM | 2026-05-08 08:55 PM | Implemented `_parse_model_output()` — handles raw JSON, markdown code blocks, filters unknown attributes, validates range |
| 3.3 | Completed | 2026-05-08 08:45 PM | 2026-05-08 08:55 PM | Implemented `_should_flag_for_review()` in `vision/pipeline.py` — flags low confidence, conflicting attributes, unusual media types |
| 3.4 | Completed | 2026-05-08 08:35 PM | 2026-05-08 08:38 PM | `vision/loader.py` already created in Phase 2 — `write_image_attributes()` stores base + derived labels |
| 3.5 | Completed | 2026-05-08 08:55 PM | 2026-05-08 09:00 PM | Added `vision-tag` CLI subcommand — `--limit`, `--changed-only`, `--model`, `--model-version`, `--mock` |
| 3.6 | Completed | 2026-05-08 08:55 PM | 2026-05-08 09:00 PM | `vision/pipeline.py` generates `outputs/vision/image_attributes.json` with full structured output per image |
| 3.7 | Completed | 2026-05-08 09:00 PM | 2026-05-08 09:08 PM | Added `tests/test_vision_tagger.py` — 16 tests: parsing, mock tagger, review flags, full pipeline with mock |
| 3.8 | Completed | 2026-05-08 09:08 PM | 2026-05-08 09:10 PM | 201 tests pass, ruff clean |

### Phase 3 Summary

- **Changes:** Created `vision/tagger.py` (VisionTagger with Qwen2.5-VL + MockTagger), `vision/pipeline.py` (orchestration, review flagging, JSON output). Added `vision-tag` CLI command with `--mock` flag for GPU-less testing. 16 new tests in `test_vision_tagger.py`. 201 tests pass, ruff clean.
- **Changes hosted at:** `src/artemis_calendar/vision/tagger.py`, `vision/pipeline.py`, `cli.py`
- **Commit:** `feat(vision): add local image tagging with Qwen2.5-VL and attribute extraction`

---

## Phase 4: Embeddings and Clustering

**Goal:** `artemis vision embed-images` generates SigLIP embeddings, `artemis vision cluster-images` runs HDBSCAN/K-Means, `artemis vision summarize-clusters` produces labeled cluster summaries. Cluster review output generated.
**Depends on:** Phase 3 (needs attribute labels for cluster labeling).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 4.1 | Completed | 2026-05-08 09:15 PM | 2026-05-08 09:15 PM | Existing `features/embeddings.py` already supports multiple models via `embedding_model_version` — SigLIP can be added as a new version string. No new file needed. |
| 4.2 | Completed | 2026-05-08 09:15 PM | 2026-05-08 09:15 PM | Decided to reuse existing `feature_image_cluster` flat table (additive, no breaking changes) rather than adding normalized tables. Existing 168+ tests depend on this schema. |
| 4.3 | Completed | 2026-05-08 09:15 PM | 2026-05-08 09:15 PM | Existing `cluster/clustering.py` already has K-Means + HDBSCAN with multimodal support. No new clustering file needed. |
| 4.4 | Completed | 2026-05-08 09:15 PM | 2026-05-08 09:25 PM | Created `vision/cluster_labels.py` — label generation from dominant attributes, label update in DB, representative/outlier image selection |
| 4.5 | Completed | 2026-05-08 09:25 PM | 2026-05-08 09:30 PM | Added `vision-label-clusters` CLI command with `--run-id`, `--cluster-type`, `--export-review` flags |
| 4.6 | Completed | 2026-05-08 09:25 PM | 2026-05-08 09:30 PM | `export_cluster_review()` generates `cluster_review.json` and `cluster_review.md` with full cluster detail |
| 4.7 | Completed | 2026-05-08 09:30 PM | 2026-05-08 09:35 PM | Added `tests/test_vision_clusters.py` — 10 tests: label generation, DB labeling, JSON/MD export, edge cases |
| 4.8 | Completed | 2026-05-08 09:35 PM | 2026-05-08 09:37 PM | 211 tests pass, ruff clean |

### Phase 4 Summary

- **Changes:** Created `vision/cluster_labels.py` (label generation, review export). Added `vision-label-clusters` CLI command. Reused existing embedding and clustering infrastructure rather than duplicating. 10 new tests in `test_vision_clusters.py`. 211 tests pass, ruff clean.
- **Changes hosted at:** `src/artemis_calendar/vision/cluster_labels.py`, `cli.py`
- **Commit:** `feat(vision): add cluster labeling from dominant attributes and review export`

---

## Phase 5: Voting Block Config Schema

**Goal:** Voting block config schema validated via Pydantic, dry-run reports image match counts per block, config stored in `config/voting_blocks/`.
**Depends on:** Phase 2 (needs attribute vocabulary for rule validation).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 5.1 | Open | | | Create `config/voting_blocks/` directory and example `earth_moon_bias_test.yaml` — scenario with 4 blocks per design section 8.2 |
| 5.2 | Open | | | Create `src/artemis_calendar/vision/voting_config.py` — Pydantic models: `VotingScenario`, `VotingBlock`, `PreferenceRule` (all_of, any_of, none_of, weighted_attributes) |
| 5.3 | Open | | | Implement config loading and validation — parse YAML, validate attribute codes against vocabulary, check block IDs unique, validate rule structure |
| 5.4 | Open | | | Add warehouse tables: `dim_voting_scenario`, `dim_voting_block`, `voting_block_rule` — per design section 10.4 |
| 5.5 | Open | | | Implement dry-run: match images against each block's rules, report matching image counts, flag blocks with low match counts |
| 5.6 | Open | | | Add `votes validate-block-config` CLI subcommand — `--config`, `--dry-run`, output validation summary to `outputs/voting_blocks/config_validation_summary.json` |
| 5.7 | Open | | | Add tests: config parsing, validation errors (bad attribute, duplicate block ID), dry-run output, low-match-count warning |
| 5.8 | Open | | | Run pytest + ruff, fix any issues, stage and commit |

### Phase 5 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(votes): add voting block config schema, validation, and dry-run`

---

## Phase 6: Voting Block Generator

**Goal:** `artemis votes generate-blocks` creates synthetic voters assigned to blocks, generates attribute-biased votes using utility function, writes synthetic run metadata.
**Depends on:** Phase 5 (config schema) + Phase 3 (image attributes for utility function).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 6.1 | Open | | | Create `src/artemis_calendar/synthetic/block_generator.py` — create voters per block config, assign to `synthetic_voter_block_assignment` |
| 6.2 | Open | | | Implement attribute-based utility function — `baseline_quality + attribute_match_score + cluster_preference + latent_appeal + randomness - none_of_penalty` per design section 8.4 |
| 6.3 | Open | | | Implement vote generation — for each voter, compute utility per candidate image, select top-k with stochastic sampling weighted by utility |
| 6.4 | Open | | | Write synthetic run metadata — `synthetic_run_id`, `scenario_id`, seed, config hash, voter/vote counts |
| 6.5 | Open | | | Add `votes generate-blocks` CLI subcommand — `--config`, `--run-name`, `--seed`, `--replace-run`, `--append-run`, `--dry-run`, `--voter-count-multiplier`, `--votes-per-voter`, `--output-summary`, `--write-review-files` |
| 6.6 | Open | | | Generate `outputs/voting_blocks/generated_vote_summary.json` — per-block voter count, vote count, top images, attribute match stats |
| 6.7 | Open | | | Add tests: voter assignment, utility calculation, vote distribution bias, seed reproducibility, replace-run idempotency |
| 6.8 | Open | | | Run pytest + ruff, fix any issues, stage and commit |

### Phase 6 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(votes): add voting block generator with attribute-biased utility function`

---

## Phase 7: Block-Aware Statistics

**Goal:** Mart tables calculated: attribute lift, cluster lift, block similarity, score impact, calendar impact, bias detection status. All block-level analysis queries work.
**Depends on:** Phase 6 (needs generated votes).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 7.1 | Open | | | Add mart tables: `mart_voting_block_summary`, `mart_voting_block_attribute_lift`, `mart_voting_block_cluster_lift`, `mart_voting_block_image_lift`, `mart_voting_block_similarity`, `mart_voting_block_score_impact`, `mart_voting_block_calendar_impact` |
| 7.2 | Open | | | Implement attribute lift calculation — per-block selection rate vs global, lift ratio, odds ratio, confidence intervals (design section 11.3) |
| 7.3 | Open | | | Implement cluster lift calculation — per-block cluster selection rate vs global, chi-square contribution (design section 11.4) |
| 7.4 | Open | | | Implement block similarity — Jaccard top-N, cosine similarity, score correlation, overlap counts (design section 11.5) |
| 7.5 | Open | | | Implement score impact — score with/without block, delta, rank movement, block influence score (design section 11.6) |
| 7.6 | Open | | | Implement calendar impact — calendar set with/without blocks, changed months, cover change, diversity/attribute/cluster deltas (design section 11.7) |
| 7.7 | Open | | | Implement bias detection result — intended vs detected bias, detection strength, evidence, confidence, status (design section 11.8) |
| 7.8 | Open | | | Add `stats compute-block-analysis` and `stats compute-calendar-impact` CLI subcommands |
| 7.9 | Open | | | Add tests: lift calculations against known synthetic scenario, similarity matrix symmetry, score impact sums, detection status logic |
| 7.10 | Open | | | Run pytest + ruff, fix any issues, stage and commit |

### Phase 7 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(stats): add block-aware statistics — lift, similarity, score impact, calendar impact, detection`

---

## Phase 8: Static API Export

**Goal:** Static JSON files generated for all new analysis — vision summary, clusters, voting block summary, attribute lift, cluster lift, score impact, calendar impact. Files land in `_site_new/api/`.
**Depends on:** Phase 7 (needs mart tables populated).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 8.1 | Open | | | Create `src/artemis_calendar/static/exporter.py` (or extend existing static build) — query mart tables, serialize to JSON, write to `_site_new/api/` |
| 8.2 | Open | | | Export `api/vision-summary.json` — attribute counts, confidence distributions, review flag counts |
| 8.3 | Open | | | Export `api/clusters.json` — cluster ID, label, summary, image count, dominant attributes, representative image IDs |
| 8.4 | Open | | | Export `api/voting-block-summary.json` — scenario metadata, per-block summary cards (voter count, vote count, top attributes, detection status) |
| 8.5 | Open | | | Export `api/voting-block-attribute-lift.json`, `api/voting-block-cluster-lift.json`, `api/voting-block-score-impact.json`, `api/voting-block-calendar-impact.json` |
| 8.6 | Open | | | Add `stats export-static-json` CLI subcommand — `--output-dir` (default `_site_new/api/`) |
| 8.7 | Open | | | Sanitize exports — verify no raw voter records, no local paths, no seeds, no model prompts, no admin metadata leak |
| 8.8 | Open | | | Add tests: JSON schema validation, no-PII checks, file existence after export |
| 8.9 | Open | | | Run pytest + ruff, fix any issues, stage and commit |

### Phase 8 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(static): export block-aware analysis to static JSON for public site`

---

## Phase 9: Static Website Update

**Goal:** `_site_new/` stats page displays all new analysis sections — voting bias, vision labels, clusters, attribute/cluster lift, block similarity, score impact, calendar impact. No admin controls exposed.
**Depends on:** Phase 8 (needs static JSON files).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 9.1 | Open | | | Add Voting Scenario Summary section to stats page — scenario name, date, voter/vote/block counts, overall detection result |
| 9.2 | Open | | | Add Voting Block Summary cards — one card per block with name, rule summary, voter/vote counts, top attributes, lift, detection status |
| 9.3 | Open | | | Add Vision Label Summary section — attribute counts, bar chart, confidence distribution |
| 9.4 | Open | | | Add Cluster Summary section — cluster gallery with label, representative images, image count, dominant attributes, top voting block |
| 9.5 | Open | | | Add Attribute Lift heatmap — blocks × attributes, lift values, color scale |
| 9.6 | Open | | | Add Cluster Lift heatmap — blocks × clusters, lift values |
| 9.7 | Open | | | Add Block Similarity matrix — pairwise Jaccard/cosine/correlation |
| 9.8 | Open | | | Add Score Impact section — most promoted/suppressed images, rank movement chart |
| 9.9 | Open | | | Add Calendar Impact section — changed months, cover change, diversity delta |
| 9.10 | Open | | | Verify no admin controls exposed — no POST forms, no generation buttons, no config editors, no raw voter data, no local paths, no seeds |
| 9.11 | Open | | | Add responsive styling via Atlas design system (tokens.css + system.css) |
| 9.12 | Open | | | Run pytest + ruff, fix any issues, stage and commit |

### Phase 9 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add voting bias analysis, vision labels, and cluster views to static site`

---

## Phase 10: Acceptance Tests and Validation

**Goal:** Known synthetic scenarios pass end-to-end — Earth+Moon, Earth-only, Moon+Sun, neutral control, random voters, edge cases. All acceptance criteria from design section 17 verified.
**Depends on:** Phase 9 (full pipeline must exist).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 10.1 | Open | | | Create test scenario fixture: `earth_moon_bias_test.yaml` with 4 blocks (Earth+Moon 25 voters, Earth-only 20, Moon+Sun 30, neutral 50) |
| 10.2 | Open | | | Add acceptance test: CLI generates expected voter counts per block |
| 10.3 | Open | | | Add acceptance test: CLI generates expected vote counts per block |
| 10.4 | Open | | | Add acceptance test: attribute rules match expected images (Earth+Moon block selects earth_and_moon images at higher rate) |
| 10.5 | Open | | | Add acceptance test: biased blocks produce measurable attribute lift (>1.0x for target attributes) |
| 10.6 | Open | | | Add acceptance test: cluster lift is calculated and non-trivial for biased blocks |
| 10.7 | Open | | | Add acceptance test: score impact is calculated — score delta and rank delta exist for each block |
| 10.8 | Open | | | Add acceptance test: static JSON files are generated with correct schema |
| 10.9 | Open | | | Add acceptance test: stats page displays aggregate results (check rendered HTML/JSON endpoints) |
| 10.10 | Open | | | Add acceptance test: stats page exposes no admin controls — no POST endpoints, no generation forms, no raw voter data |
| 10.11 | Open | | | Add edge case test: low-confidence label case — images with conflicting attributes flagged for review |
| 10.12 | Open | | | Add edge case test: small matching-image-count block — warning generated, votes still produced with fallback |
| 10.13 | Open | | | Run full pytest suite, verify all pass, ruff clean |
| 10.14 | Open | | | Stage and commit |

### Phase 10 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `test: add acceptance tests for biased voting blocks and static reporting`

---

## Phase 11: Lessons Learned

**Goal:** Extract lessons learned from the full implementation. Document design decisions, surprises, reusable patterns, and mistakes from each phase.
**Depends on:** Phase 10 (all implementation complete).

| Task | Status | Started (PST) | Completed (PST) | Description |
|------|--------|---------------|------------------|-------------|
| 11.1 | Open | | | Run `/lessons` skill — extract lessons from vision tagging pipeline (model selection, prompt engineering, confidence calibration) |
| 11.2 | Open | | | Run `/lessons` skill — extract lessons from embedding + clustering (SigLIP vs CLIP, HDBSCAN vs K-Means trade-offs, cluster labeling) |
| 11.3 | Open | | | Run `/lessons` skill — extract lessons from voting block design (config schema, utility function tuning, edge cases) |
| 11.4 | Open | | | Run `/lessons` skill — extract lessons from block-aware statistics (lift calculation, similarity metrics, calendar impact measurement) |
| 11.5 | Open | | | Run `/lessons` skill — extract lessons from static site integration (JSON export sanitization, visualization choices, Atlas design system reuse) |
| 11.6 | Open | | | Run `/lessons` skill — extract lessons from acceptance testing (synthetic scenario design, end-to-end validation, edge case coverage) |
| 11.7 | Open | | | Review and consolidate lessons — ensure no duplicates, cross-reference with existing `docs/lessons/`, update lessons index |
| 11.8 | Open | | | Stage and commit |

### Phase 11 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `docs: add lessons learned from biased voting blocks implementation`
