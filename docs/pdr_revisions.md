# Additions to the PDR

## 1. Add to Project Purpose

This project is also a **learning and architecture-demonstration project**. In addition to producing a defensible calendar image-selection process, the repository should document the architecture, design decisions, statistical methods, clustering methods, pipeline structure, and lessons learned during development. The goal is to make the project useful as both a data science project and a public example of applied data engineering.

---

## 2. Add to Source Architecture

Use `github.com/bonjohen/jobclass` as the reference architecture for the extract/load/publish pipeline.

The JobClass repository uses a layered warehouse pattern: **Raw → Staging → Core → Marts**, with raw immutable source capture, parsed typed staging tables, conformed warehouse dimensions/facts/bridges, and query-ready analytical marts. It also separates code into `extract`, `parse`, `load`, `validate`, `observe`, `orchestrate`, and `marts`, with source manifests, idempotent pipeline execution, schema drift detection, validation gates, run manifests, tests, and lesson pages. ([GitHub][1])

The Artemis calendar project should reuse that architectural pattern:

```text
src/artemis_calendar/
  config/        Source manifests, settings, paths
  extract/       Download source pages, manifests, images, vote data
  archive/       Immutable raw snapshot storage
  parse/         Source-specific parsers
  load/          Staging and warehouse loaders
  validate/      Schema, grain, referential, drift, and semantic checks
  observe/       Run manifests, logs, metrics
  features/      Image embeddings, text embeddings, sentiment, clustering
  models/        Preference models, reliability models, scoring
  optimize/      Calendar slate generation and month assignment
  marts/         Analyst-facing outputs
  reports/       Markdown/HTML review packages
  lessons/       Lessons learned and architecture explanations
  tests/         Unit, warehouse, integration, and model tests
```

---

## 3. Add to Functional Requirements

| ID     | Requirement                                                                                       | Priority |
| ------ | ------------------------------------------------------------------------------------------------- | -------- |
| FR-023 | Archive every downloaded source snapshot immutably                                                | Must     |
| FR-024 | Regularly check ArtemisTimeline and voting data sources for new or changed data                   | Must     |
| FR-025 | Maintain source manifests with URL, retrieval timestamp, content hash, and load status            | Must     |
| FR-026 | Detect schema drift, manifest drift, and image metadata drift                                     | Must     |
| FR-027 | Generate image embeddings for visual clustering                                                   | Must     |
| FR-028 | Generate text embeddings from image descriptions                                                  | Must     |
| FR-029 | Cluster images by visual similarity                                                               | Must     |
| FR-030 | Cluster images by description/topic similarity                                                    | Must     |
| FR-031 | Support combined multimodal clustering using image and description features                       | Should   |
| FR-032 | Produce top-N image picks within each cluster                                                     | Must     |
| FR-033 | Allow cluster collapsing in reports so similar images can be reviewed as groups                   | Must     |
| FR-034 | Score images for month suitability and cover suitability                                          | Must     |
| FR-035 | Use description sentiment, subject, visual tone, and mission phase as calendar-placement features | Should   |
| FR-036 | Track lessons learned during project development                                                  | Must     |
| FR-037 | Document architectural patterns and explain why each is used                                      | Must     |
| FR-038 | Publish methodology notes suitable for a learning portfolio                                       | Should   |

---

## 4. Add Archive and Refresh Pipeline

The project should not treat Artemis data as a one-time download. The source material, leaderboards, and vote summaries may change over time. The pipeline should therefore perform regular refresh checks and preserve every meaningful version.

The Artemis vote page currently describes roughly 12,000 mission photos, a 7,000+ usable-frame random-batch pool, head-to-head Elo voting, random batches of 50 images with 5 selected favorites, and category ranking by top 3 photos. ([Artemis Timeline][2]) The timeline page currently presents 220 photos/videos and advertises the FARTHER 2027 calendar as a 13-month calendar using Artemis II mission photography. ([Artemis Timeline][3])

### Archive Layout

```text
data/
  raw/
    artemistimeline/
      site_snapshot/
        load_date=YYYY-MM-DD/
      vote_page/
        load_date=YYYY-MM-DD/
      image_manifest/
        load_date=YYYY-MM-DD/
      metadata/
        load_date=YYYY-MM-DD/
      leaderboard_overall/
        load_date=YYYY-MM-DD/
      leaderboard_elo/
        load_date=YYYY-MM-DD/
      leaderboard_category/
        load_date=YYYY-MM-DD/
      raw_votes/
        load_date=YYYY-MM-DD/
  staging/
  warehouse/
  marts/
  reports/
```

### Refresh Process

| Step | Process                                                     |
| ---- | ----------------------------------------------------------- |
| 1    | Fetch known source URLs                                     |
| 2    | Compute content hash                                        |
| 3    | Compare against prior snapshot                              |
| 4    | Archive new or changed content                              |
| 5    | Parse into staging                                          |
| 6    | Validate schema and grain                                   |
| 7    | Load warehouse tables                                       |
| 8    | Rebuild feature tables if image or description data changed |
| 9    | Recompute affected scores and clusters                      |
| 10   | Produce change report                                       |

### Refresh Modes

| Mode                  | Purpose                                     |
| --------------------- | ------------------------------------------- |
| `snapshot-refresh`    | Download and archive source pages/manifests |
| `metadata-refresh`    | Parse and load image metadata               |
| `leaderboard-refresh` | Capture aggregate vote summaries            |
| `vote-refresh`        | Load raw vote exports, if provided          |
| `feature-refresh`     | Recompute image/text features               |
| `cluster-refresh`     | Rebuild visual/text/multimodal clusters     |
| `score-refresh`       | Recompute image preference scores           |
| `calendar-refresh`    | Regenerate calendar candidates              |
| `publish-report`      | Build review-ready reports                  |

---

## 5. Add Cluster Analysis Design

The project should perform cluster analysis at three levels:

1. **Image clustering**
2. **Description clustering**
3. **Multimodal clustering**

The purpose is not only modeling. It also supports practical review workflows:

* collapse visually similar groups;
* show top few picks from each group;
* avoid redundant calendar selections;
* discover underrepresented image families;
* compare voter preference by cluster;
* select a better calendar collection than top-N rankings.

---

## 6. Image Clustering

Image clustering should use visual embeddings generated from thumbnails or full-resolution images.

### Candidate Methods

| Method                   | Use                                               |
| ------------------------ | ------------------------------------------------- |
| CLIP / SigLIP embeddings | General visual similarity                         |
| PCA / UMAP               | Dimensionality reduction and visualization        |
| HDBSCAN                  | Find natural clusters without fixed cluster count |
| k-means                  | Produce controlled fixed-number cluster sets      |
| Agglomerative clustering | Hierarchical review and cluster collapsing        |
| Cosine similarity        | Pairwise redundancy scoring                       |

### Image Cluster Outputs

| Output                            | Purpose                                   |
| --------------------------------- | ----------------------------------------- |
| `image_cluster_id`                | Group similar images                      |
| `cluster_label`                   | Human-readable cluster name               |
| `cluster_representative_image_sk` | Best representative image                 |
| `cluster_size`                    | Number of images in group                 |
| `cluster_top_images`              | Highest-scoring images in cluster         |
| `cluster_diversity_score`         | Internal visual spread                    |
| `cluster_calendar_value`          | Whether the group deserves representation |

---

## 7. Description Clustering

Description clustering should use text from title, description, camera, location, mission phase, and any available metadata.

### Candidate Text Features

| Feature               | Use                                        |
| --------------------- | ------------------------------------------ |
| Description embedding | Semantic similarity                        |
| TF-IDF terms          | Interpretable keyword clustering           |
| Topic model           | Subject grouping                           |
| Sentiment score       | Month/cover suitability                    |
| Emotion/tone score    | Mood matching                              |
| Named entities        | Earth, Moon, Orion, crew, spacecraft, etc. |
| Mission phase         | Chronological coverage                     |

### Description Cluster Outputs

| Output                        | Purpose                        |
| ----------------------------- | ------------------------------ |
| `description_cluster_id`      | Semantic group                 |
| `topic_label`                 | Human-readable topic           |
| `top_terms`                   | Interpretable cluster keywords |
| `representative_descriptions` | Explain cluster content        |
| `sentiment_mean`              | Average emotional tone         |
| `month_affinity`              | Possible month fit             |
| `cover_affinity`              | Possible cover fit             |

---

## 8. Multimodal Clustering

Multimodal clustering should combine visual embeddings and description embeddings. This will help distinguish cases where images look similar but mean different things, or where descriptions are similar but images have different aesthetic value.

Example:

| Case                                                 | Handling                                              |
| ---------------------------------------------------- | ----------------------------------------------------- |
| Same visual look, different mission moment           | Keep separate if story value differs                  |
| Same description topic, different visual composition | Cluster semantically but preserve visual alternatives |
| High visual appeal, weak description                 | Candidate for image-led selection                     |
| Strong mission description, weak visual appeal       | Candidate for article/report but not calendar         |
| Similar Earth/Moon views                             | Collapse and show top few picks                       |

### Combined Cluster Score

A practical combined similarity score:

```text
combined_similarity =
  visual_similarity_weight * visual_similarity
+ text_similarity_weight * description_similarity
+ metadata_similarity_weight * metadata_similarity
```

Initial weights:

| Component              | Weight |
| ---------------------- | -----: |
| Visual similarity      |   0.60 |
| Description similarity |   0.30 |
| Metadata similarity    |   0.10 |

These should be configurable and documented in the model-run parameters.

---

## 9. Add Cluster Mart Tables

### `mart_image_cluster_summary`

| Column                     | Description                       |
| -------------------------- | --------------------------------- |
| `cluster_run_id`           | Cluster model run                 |
| `cluster_type`             | visual, text, multimodal          |
| `cluster_id`               | Cluster identifier                |
| `cluster_label`            | Human-readable label              |
| `image_count`              | Number of images                  |
| `top_image_sk`             | Best-scoring representative       |
| `mean_preference_score`    | Average image score               |
| `max_preference_score`     | Best image score                  |
| `mean_sentiment_score`     | Average description sentiment     |
| `calendar_candidate_count` | Times used in generated calendars |
| `review_priority`          | high, medium, low                 |
| `notes`                    | Reviewer notes                    |

### `mart_cluster_top_images`

| Column               | Description                               |
| -------------------- | ----------------------------------------- |
| `cluster_run_id`     | Cluster model run                         |
| `cluster_type`       | visual, text, multimodal                  |
| `cluster_id`         | Cluster identifier                        |
| `image_sk`           | Image key                                 |
| `rank_in_cluster`    | Rank within cluster                       |
| `preference_score`   | Image appeal score                        |
| `selection_rate`     | Batch selection rate                      |
| `elo_score`          | Pairwise score                            |
| `borda_score`        | Category score                            |
| `diversity_value`    | Value relative to other images in cluster |
| `recommended_action` | select, alternate, suppress, review       |

---

## 10. Add Month and Cover Suitability Scoring

Some images will be better for specific calendar months or for the cover. Month assignment should be treated as a scoring problem, not an afterthought.

### Month Suitability Inputs

| Input                  | Use                                              |
| ---------------------- | ------------------------------------------------ |
| Description sentiment  | Mood fit                                         |
| Description topic      | Seasonal or narrative fit                        |
| Dominant color palette | Month aesthetic                                  |
| Brightness/contrast    | Print suitability                                |
| Subject matter         | Earth, Moon, spacecraft, crew, eclipse, interior |
| Mission phase          | Chronological calendar flow                      |
| Visual drama           | Cover or key-month suitability                   |
| Composition            | Cropping and typography suitability              |
| Image orientation      | Calendar layout fit                              |

### Cover Suitability

The cover image should be scored separately because it has a different job than a month image.

Cover image traits:

1. high immediate visual impact;
2. clear subject;
3. works at thumbnail size;
4. has room for title typography;
5. represents the mission broadly;
6. is not too visually busy;
7. has strong emotional or symbolic value;
8. has broad voter appeal.

### `mart_image_calendar_slot_score`

| Column                    | Description                    |
| ------------------------- | ------------------------------ |
| `slot_score_run_id`       | Run identifier                 |
| `image_sk`                | Image key                      |
| `slot_type`               | month, cover, bonus            |
| `slot_number`             | 1-13, nullable for cover       |
| `slot_label`              | January, February, Cover, etc. |
| `preference_score`        | General image appeal           |
| `sentiment_score`         | Description sentiment          |
| `visual_mood_score`       | Visual tone                    |
| `seasonal_fit_score`      | Month fit                      |
| `mission_story_fit_score` | Chronological/narrative fit    |
| `typography_space_score`  | Cover/layout usability         |
| `print_quality_score`     | Technical suitability          |
| `total_slot_score`        | Combined score                 |
| `reason`                  | Human-readable explanation     |

---

## 11. Add Documentation and Lessons Learned

Because this is a learning project, documentation should be a first-class output.

### Documentation Structure

```text
docs/
  00_project_overview.md
  01_pdr.md
  02_data_sources.md
  03_pipeline_architecture.md
  04_warehouse_design.md
  05_vote_modeling.md
  06_voter_surrogate_keys.md
  07_image_clustering.md
  08_description_clustering.md
  09_multimodal_clustering.md
  10_inter_rater_reliability.md
  11_calendar_optimization.md
  12_month_and_cover_scoring.md
  13_privacy_and_ethics.md
  14_lessons_learned.md
  15_methodology_for_publication.md
```

### Lessons Learned Registry

Create a structured lessons registry similar in spirit to JobClass’s lesson pages and methodology documentation. JobClass includes a web lesson registry and methodology-facing pages in its project structure, plus a Pipeline Explorer release that documents the pipeline as an educational visualization. ([GitHub][1])

### `docs/lessons/` Structure

```text
docs/lessons/
  001_raw_archive_pattern.md
  002_surrogate_voter_keys.md
  003_why_not_top_n.md
  004_exposure_adjusted_voting.md
  005_krippendorff_alpha_sparse_votes.md
  006_bradley_terry_luce_for_pairwise_images.md
  007_image_embeddings_for_redundancy.md
  008_text_embeddings_for_description_clusters.md
  009_multimodal_clustering.md
  010_calendar_as_portfolio_optimization.md
  011_month_fit_scoring.md
  012_reproducible_model_runs.md
```

Each lesson should include:

1. problem;
2. why it matters;
3. design choice;
4. alternatives considered;
5. implementation notes;
6. validation method;
7. what was learned;
8. reusable pattern.

---

## 12. Add Pipeline Explorer Requirement

A later phase should include a simple static **Pipeline Explorer** page showing the project data flow.

Minimum version:

* source nodes;
* raw archive nodes;
* staging nodes;
* core warehouse nodes;
* feature nodes;
* model nodes;
* mart nodes;
* report nodes.

This mirrors the JobClass pattern where the project includes a pipeline visualization and educational pages explaining the architecture. ([GitHub][1])

---

## 13. Add to Deliverables

| Deliverable                | Description                                                                                                |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Source archive             | Immutable snapshots of ArtemisTimeline pages, manifests, metadata, leaderboards, and raw votes if provided |
| Refresh pipeline           | Regular process to detect and load new or changed source data                                              |
| Visual cluster report      | Clustered image groups with top picks from each                                                            |
| Description cluster report | Semantic/topic clusters from descriptions and metadata                                                     |
| Multimodal cluster report  | Combined visual/text clusters                                                                              |
| Cluster review UI/report   | Collapsible groups showing top candidates per group                                                        |
| Month suitability model    | Scores images for each month and cover                                                                     |
| Cover candidate report     | Separate ranking of images suitable for the calendar cover                                                 |
| Lessons learned registry   | Development notes and reusable architectural explanations                                                  |
| Architecture documentation | Explanation of why each pipeline layer and modeling method exists                                          |
| Pipeline explorer          | Static visual explanation of the data pipeline                                                             |

---

## 14. Add to Implementation Phases

### Phase 1A: JobClass Pattern Adaptation

Create the project skeleton using the JobClass-inspired architecture:

```text
extract → archive → parse → load → validate → observe → marts
```

Exit criteria:

1. source manifest exists;
2. raw archive path exists;
3. load-run manifest exists;
4. first metadata snapshot archived;
5. first staging load completes;
6. first validation report generated.

### Phase 2A: Clustering Foundation

Deliver:

1. image embeddings;
2. description embeddings;
3. visual clusters;
4. text clusters;
5. multimodal clusters;
6. top-N per cluster report.

Exit criteria:

1. clusters are reproducible by run ID;
2. every cluster has representative images;
3. redundant top-ranked images are detectable;
4. cluster summary report is reviewable.

### Phase 4A: Month and Cover Scoring

Deliver:

1. month suitability scores;
2. cover suitability scores;
3. slot-assignment model;
4. calendar candidate comparison.

Exit criteria:

1. every candidate image has month scores;
2. every candidate calendar has assigned slots;
3. cover image is selected or ranked separately;
4. selected images include explanations.

### Phase 5A: Learning Documentation

Deliver:

1. lessons learned registry;
2. architecture explanation;
3. data pipeline walkthrough;
4. method explanations;
5. final public methodology report.

Exit criteria:

1. every major architectural choice has a short explanation;
2. every major statistical method has a plain-language explanation;
3. final report explains why the optimized calendar differs from top-N ranking.

---

## 15. Add to Calendar Objective Function

Updated objective:

```text
Calendar Utility =
  image_preference_score
+ voter_consensus_score
+ visual_diversity_score
+ description_diversity_score
+ mission_phase_coverage_score
+ month_fit_score
+ cover_fit_score
+ cluster_coverage_score
- visual_redundancy_penalty
- description_redundancy_penalty
- uncertainty_penalty
- overconcentration_penalty
```

This directly supports the review goal:

**show the top few picks in each group, then select the best calendar collection across groups.**

[1]: https://github.com/bonjohen/jobclass "GitHub - bonjohen/jobclass: Labor market occupation data pipeline — ingests SOC, OEWS, O*NET, and BLS Projections into a layered analytical warehouse · GitHub"
[2]: https://artemistimeline.com/vote "Artemis II Photo Voter"
[3]: https://artemistimeline.com/ "ARTEMIS II PHOTO TIMELINE"
