# Physical Design Document

## Artemis II Calendar Image Selection Data Platform

**Document status:** Preliminary Design Review draft
**Project:** Artemis II 2027 Calendar Image Selection
**Primary objective:** Select the strongest 12- or 13-image calendar collection from Artemis II mission imagery.
**Secondary objective:** Use the project as a learning, architecture, and data science documentation project.
**Major open question:** Availability of raw voter-level records.

---

## 1. Executive Summary

This project designs a data science and data engineering platform for selecting a high-quality Artemis II calendar image collection. The goal is not to select the top 12 or 13 individual images by raw likes, Elo score, or selection rate. The goal is to select the best **calendar slate**: a coherent, diverse, high-appeal collection that balances voter preference, mission coverage, image similarity, description similarity, month suitability, cover suitability, and aesthetic flow.

The ArtemisTimeline voting site describes several useful preference-collection workflows: head-to-head image voting with a running Elo leaderboard, random-batch voting where voters see 50 images and pick 5 favorites, and category-specific ranking where voters drag their top 3 photos within a focused moment. The voting page also states that NASA released roughly 12,000 Artemis II photos and that the random-batch workflow samples from 7,000+ usable frames. ([Artemis Timeline][1])

The ArtemisTimeline main site presents Artemis II photo and video material from March-April 2026. It currently shows 220 media items and includes metadata fields such as time, distance from Earth, distance to Moon, photographer, location, camera, settings, and description. It also advertises **FARTHER — 2027 Calendar** as a 13-month calendar using Artemis II mission photography. ([Artemis Timeline][2])

This project will use a layered data pipeline modeled after the user’s JobClass repository, which uses a Raw → Staging → Core → Marts warehouse pattern, immutable raw capture, typed staging, conformed dimensions/facts/bridges, analytical marts, idempotent execution, schema drift detection, validation gates, and structured pipeline modules. ([GitHub][3])

---

## 2. PDR Purpose

The Preliminary Design Review evaluates whether the proposed architecture is complete enough to proceed into implementation planning.

The PDR should confirm:

1. The problem is correctly framed as **collection optimization**, not top-N ranking.
2. The data model supports raw voter data if it becomes available.
3. The data model still supports useful analysis if only public aggregates are available.
4. Voter identities are handled through surrogate keys and privacy-preserving hashes.
5. Batch voting, pairwise voting, and category ranking are modeled at their natural grain.
6. Image clustering, description clustering, and multimodal clustering are first-class parts of the design.
7. Month suitability and cover suitability are included.
8. Data extraction, archival, refresh, validation, and publication are covered.
9. Lessons learned and architecture documentation are treated as project deliverables.
10. Acceptance criteria are clear enough to guide implementation.

---

## 3. Project Goals

## 3.1 Primary Goals

1. Build a local data warehouse for Artemis II image metadata, voting data, image features, text features, scoring outputs, clusters, and calendar candidates.
2. Preserve raw source snapshots for repeatable analysis.
3. Support anonymous voter-level analysis if raw vote data is provided.
4. Estimate image preference using statistically defensible methods.
5. Measure inter-rater agreement where raw voter-level data allows it.
6. Cluster images by visual similarity.
7. Cluster descriptions by semantic similarity.
8. Combine visual and text signals into multimodal clusters.
9. Select calendar candidates using collection-level optimization.
10. Explain why the selected calendar differs from a naive top-N leaderboard.

## 3.2 Learning Goals

1. Document the pipeline architecture.
2. Explain why each major design pattern is used.
3. Track lessons learned during implementation.
4. Build a reusable example of applied data engineering and data science.
5. Produce public-facing methodology notes.
6. Treat the repository as a learning artifact, not only a working system.

---

## 4. Scope

## 4.1 In Scope

1. Source-page and metadata download.
2. Immutable raw data archive.
3. Regular refresh checks for changed or newly available data.
4. Public leaderboard snapshot ingestion.
5. Raw vote ingestion if provided.
6. Voter surrogate-key management.
7. Image metadata warehouse.
8. Vote-event warehouse.
9. Image embedding generation.
10. Description embedding generation.
11. Sentiment and tone analysis of descriptions.
12. Visual clustering.
13. Description clustering.
14. Multimodal clustering.
15. Cluster-level top-pick reports.
16. Image-level preference scoring.
17. Inter-rater reliability analysis if raw voter data is available.
18. Calendar candidate generation.
19. Month assignment.
20. Cover candidate scoring.
21. Review-ready reports.
22. Lessons learned documentation.
23. Architecture and methodology documentation.

## 4.2 Out of Scope for Initial Implementation

1. Real-time integration with the live ArtemisTimeline voting system.
2. Public voter-facing UI.
3. User authentication.
4. Direct calendar ordering or ecommerce integration.
5. Final print production.
6. Full rights-management workflow.
7. Attempting to identify voters.
8. Storing personally identifiable information unless explicitly authorized and necessary.
9. Automated final aesthetic approval without human review.

---

## 5. Source Summary

## 5.1 ArtemisTimeline Main Site

The ArtemisTimeline main site provides the mission-context image viewer. It shows the timeline period as March-April 2026, presents 220 photos and videos, includes media filters, and exposes image metadata fields including time, distance from Earth, distance to Moon, photographer, location, camera, settings, and description. ([Artemis Timeline][2])

Important source fields:

| Field               | Use                                                   |
| ------------------- | ----------------------------------------------------- |
| Time                | Mission chronology and month/slot narrative fit       |
| Distance from Earth | Mission phase and story context                       |
| Distance to Moon    | Mission phase and story context                       |
| Photographer        | Source diversity and attribution                      |
| Location            | Image grouping and mission context                    |
| Camera              | Source/camera diversity                               |
| Settings            | Technical review                                      |
| Description         | Text clustering, sentiment, topic modeling, month fit |
| Media type          | Photo/video filtering                                 |
| Camera filter       | Visual/source segmentation                            |

## 5.2 ArtemisTimeline Voting Site

The voting site describes three preference-collection modes:

| Mode             | Description                                                     | Data Science Use                                  |
| ---------------- | --------------------------------------------------------------- | ------------------------------------------------- |
| Head-to-head     | Featured photos go head-to-head, with a running Elo leaderboard | Pairwise preference modeling                      |
| Random batch     | Voter sees 50 random photos and picks 5 favorites               | Exposure-adjusted selection modeling              |
| Category ranking | Voter drags top 3 photos in each category                       | Category-specific ranking and Borda-style scoring |

The voting page states that the random-batch process samples across 7,000+ usable frames and that live rankings update with every vote. ([Artemis Timeline][1])

## 5.3 JobClass Reference Architecture

The JobClass repository is a useful reference for this project because it already implements a serious data pipeline with a layered warehouse, extraction modules, parsing modules, validation, observation, orchestration, marts, tests, and a web/publication layer. The README describes a four-layer warehouse: Raw, Staging, Core, and Marts. It also states that the pipeline is idempotent and that schema drift blocks publication until resolved. ([GitHub][3])

JobClass project structure includes modules for config, extract, parse, load, validate, observe, orchestrate, marts, web, tests, migrations, source manifests, and deployment scripts. ([GitHub][3])

The Artemis calendar project should reuse this general architectural style, adapted to imagery, voter data, clustering, model runs, and calendar optimization.

---

## 6. Design Principle

The system must preserve data at the natural grain of each source process.

Do not collapse raw voting data into a single image score too early.

The platform should preserve:

1. Image metadata.
2. Source image identifiers.
3. Raw source snapshots.
4. Voter surrogate keys.
5. Source voter identifier hashes.
6. Vote sessions.
7. Batch exposures.
8. Batch selections.
9. Pairwise winners and losers.
10. Category ranking positions.
11. Image embeddings.
12. Description embeddings.
13. Visual clusters.
14. Description clusters.
15. Multimodal clusters.
16. Calendar candidate membership.
17. Month assignments.
18. Cover suitability scores.
19. Run-control metadata.
20. Lessons learned.

---

## 7. Design Problem

## 7.1 Naive Approach

The naive approach is to select the top 12 or 13 images by a leaderboard metric.

Examples:

1. Top 13 by Elo.
2. Top 13 by selection rate.
3. Top 13 by category score.
4. Top 13 by raw likes.

This will likely over-select similar images.

## 7.2 Correct Approach

The correct approach is constrained portfolio optimization.

The selected calendar should maximize:

1. Image preference.
2. Broad voter appeal.
3. Confidence in the score.
4. Diversity across visual clusters.
5. Diversity across description clusters.
6. Diversity across mission phase.
7. Month suitability.
8. Cover suitability.
9. Narrative flow.
10. Print/layout suitability.

It should penalize:

1. Redundancy.
2. Overrepresentation of a single visual group.
3. Overrepresentation of a single description topic.
4. Low-confidence images.
5. Poor month fit.
6. Poor cover fit.
7. Weak technical quality.
8. Repetitive emotional tone.

---

## 8. Operating Modes

## 8.1 Aggregate-Only Mode

This mode assumes raw voter data is unavailable.

Available data may include:

1. Image metadata.
2. Public page content.
3. Public leaderboard summaries.
4. Public category results.
5. Image files or thumbnails.
6. Text descriptions.

Supported analysis:

1. Basic image ranking from available summaries.
2. Visual clustering.
3. Description clustering.
4. Multimodal clustering.
5. Month and cover suitability scoring.
6. Redundancy control.
7. Candidate calendar generation.
8. Public methodology report.

Not supported:

1. True voter-level inter-rater reliability.
2. Krippendorff’s alpha from raw voter-image matrices.
3. Voter segmentation.
4. Repeated-voter consistency.
5. Full exposure-adjusted modeling unless exposure counts are available.

## 8.2 Raw-Vote Mode

This mode assumes anonymized raw vote records are provided.

Supported analysis:

1. Exposure-adjusted selection rates.
2. Voter-image rating matrices.
3. Krippendorff’s alpha.
4. Fleiss’ kappa where applicable.
5. Kendall’s W for rankings.
6. Bradley-Terry-Luce modeling.
7. Elo recomputation.
8. Voter-level random effects.
9. Voter consistency.
10. Mode-to-mode agreement.
11. Cluster-level voter preference.
12. Stronger candidate calendar optimization.

---

## 9. Open Data Access Question

Raw voter-level data remains an open question.

The project should request anonymized data from the site owner.

Needed exports:

1. Random-batch ballot records.
2. Pairwise vote records.
3. Category ranking records.
4. Stable image manifest.
5. Stable image metadata snapshot.
6. Public aggregate leaderboard snapshots.
7. Documentation of voter identifier behavior.

Required voter-data fields, if available:

| Field            | Purpose                             |
| ---------------- | ----------------------------------- |
| Source voter ID  | Anonymous continuity across votes   |
| Vote mode        | Batch, pairwise, category           |
| Timestamp        | Session ordering and drift analysis |
| Images shown     | Exposure modeling                   |
| Images selected  | Preference modeling                 |
| Winner image     | Pairwise modeling                   |
| Loser image      | Pairwise modeling                   |
| Rank position    | Category ranking                    |
| Category ID      | Category-specific analysis          |
| Display position | Position-bias analysis              |
| User-agent class | Optional coarse quality control     |
| Server timestamp | Reliable event ordering             |

Privacy request:

1. No raw IP addresses.
2. Prefer hashed voter IDs.
3. Prefer reduced user-agent class rather than full user-agent.
4. No attempt to identify voters.
5. Aggregate-only publication.

---

## 10. Architecture Overview

## 10.1 Layered Data Architecture

The project should use the following layers:

| Layer              | Purpose                                                     |
| ------------------ | ----------------------------------------------------------- |
| Raw Archive        | Immutable source capture                                    |
| Staging            | Parsed typed source tables                                  |
| Core Warehouse     | Conformed dimensions and facts                              |
| Feature Store      | Image/text embeddings, clusters, sentiment, visual features |
| Modeling Layer     | Preference scores, agreement metrics, reliability models    |
| Optimization Layer | Calendar candidates, month assignment, cover scoring        |
| Marts              | Query-ready analytical outputs                              |
| Reports            | Review-ready and public-facing documentation                |
| Lessons            | Learning artifacts and reusable architecture explanations   |

## 10.2 Pipeline Flow

1. Extract source pages, manifests, metadata, leaderboards, and vote exports.
2. Archive raw source files with content hashes.
3. Parse raw files into staging tables.
4. Validate schema, grain, referential integrity, and semantic rules.
5. Load dimensions and facts.
6. Generate image features.
7. Generate description features.
8. Build visual clusters.
9. Build description clusters.
10. Build multimodal clusters.
11. Compute image preference scores.
12. Compute inter-rater reliability if raw data supports it.
13. Score month suitability.
14. Score cover suitability.
15. Generate candidate calendars.
16. Compare candidates to naive baselines.
17. Produce reports.
18. Record lessons learned.

---

## 11. Repository Structure

Recommended repository structure:

| Path                                | Purpose                                        |
| ----------------------------------- | ---------------------------------------------- |
| `config/`                           | Source manifests, settings, scoring parameters |
| `data/raw/`                         | Immutable source snapshots                     |
| `data/staging/`                     | Parsed intermediate outputs                    |
| `data/warehouse/`                   | Local database files or exports                |
| `data/marts/`                       | Analytical outputs                             |
| `docs/`                             | Project documentation                          |
| `docs/lessons/`                     | Lessons learned                                |
| `notebooks/`                        | Exploratory analysis                           |
| `reports/`                          | Generated reports                              |
| `scripts/`                          | CLI wrappers and utility scripts               |
| `src/artemis_calendar/config/`      | Runtime settings and path helpers              |
| `src/artemis_calendar/extract/`     | Download, manifest, refresh, version detection |
| `src/artemis_calendar/archive/`     | Immutable archive utilities                    |
| `src/artemis_calendar/parse/`       | Source-specific parsers                        |
| `src/artemis_calendar/load/`        | Staging and warehouse loaders                  |
| `src/artemis_calendar/validate/`    | Data quality and drift checks                  |
| `src/artemis_calendar/observe/`     | Logs, run manifests, metrics                   |
| `src/artemis_calendar/orchestrate/` | Pipeline orchestration                         |
| `src/artemis_calendar/features/`    | Image/text embeddings and derived features     |
| `src/artemis_calendar/models/`      | Preference and reliability models              |
| `src/artemis_calendar/cluster/`     | Visual, text, and multimodal clustering        |
| `src/artemis_calendar/optimize/`    | Calendar slate and month assignment            |
| `src/artemis_calendar/marts/`       | Mart builders                                  |
| `src/artemis_calendar/reports/`     | Report generation                              |
| `tests/`                            | Unit, integration, warehouse, and model tests  |
| `migrations/`                       | Database schema migrations                     |

---

## 12. Functional Requirements

| ID     | Requirement                                                                  | Priority |
| ------ | ---------------------------------------------------------------------------- | -------- |
| FR-001 | Load image metadata into a normalized image dimension                        | Must     |
| FR-002 | Preserve original source image identifiers                                   | Must     |
| FR-003 | Archive every downloaded source snapshot immutably                           | Must     |
| FR-004 | Maintain source manifests with URL, timestamp, content hash, and load status | Must     |
| FR-005 | Regularly check source pages and public vote data for new or changed data    | Must     |
| FR-006 | Detect source drift, schema drift, and metadata drift                        | Must     |
| FR-007 | Support raw batch-ballot ingestion if provided                               | Must     |
| FR-008 | Support raw pairwise-vote ingestion if provided                              | Must     |
| FR-009 | Support raw category-ranking ingestion if provided                           | Must     |
| FR-010 | Maintain an internal surrogate voter key                                     | Must     |
| FR-011 | Preserve source voter IDs only as hashed or restricted-access values         | Must     |
| FR-012 | Track every image shown in a batch ballot                                    | Must     |
| FR-013 | Track every selected image in a batch ballot                                 | Must     |
| FR-014 | Infer shown-but-not-selected outcomes for batch ballots                      | Must     |
| FR-015 | Track winner and loser for pairwise votes                                    | Must     |
| FR-016 | Track rank position for category rankings                                    | Must     |
| FR-017 | Compute exposure-adjusted selection rates                                    | Must     |
| FR-018 | Compute image-level preference scores                                        | Must     |
| FR-019 | Compute uncertainty metrics for image scores                                 | Must     |
| FR-020 | Compute inter-rater reliability where raw data supports it                   | Should   |
| FR-021 | Generate image embeddings for visual clustering                              | Must     |
| FR-022 | Generate text embeddings from descriptions and metadata                      | Must     |
| FR-023 | Cluster images by visual similarity                                          | Must     |
| FR-024 | Cluster images by description/topic similarity                               | Must     |
| FR-025 | Support combined multimodal clustering                                       | Should   |
| FR-026 | Produce top-N image picks within each cluster                                | Must     |
| FR-027 | Allow cluster-collapsed review outputs                                       | Must     |
| FR-028 | Score images for month suitability                                           | Must     |
| FR-029 | Score images for cover suitability                                           | Must     |
| FR-030 | Use description sentiment and tone as calendar-placement features            | Should   |
| FR-031 | Generate 12- and 13-image calendar candidates                                | Must     |
| FR-032 | Score calendar candidates using set-level objective functions                | Must     |
| FR-033 | Produce a final explainability report                                        | Must     |
| FR-034 | Support aggregate-only fallback                                              | Must     |
| FR-035 | Track lessons learned during project development                             | Must     |
| FR-036 | Document architectural patterns and explain why each is used                 | Must     |
| FR-037 | Publish methodology notes suitable for a learning portfolio                  | Should   |
| FR-038 | Compare optimized calendar slates against naive top-N baselines              | Must     |

---

## 13. Nonfunctional Requirements

| ID      | Requirement          | Target                                                       |
| ------- | -------------------- | ------------------------------------------------------------ |
| NFR-001 | Reproducibility      | Every scoring, clustering, and optimization run has a run ID |
| NFR-002 | Auditability         | Raw source files are preserved unchanged                     |
| NFR-003 | Privacy              | Analytics use surrogate voter keys, not raw identifiers      |
| NFR-004 | Portability          | Local-first design                                           |
| NFR-005 | Scalability          | Support 12,000+ images and large vote tables                 |
| NFR-006 | Extensibility        | Additional vote modes can be added                           |
| NFR-007 | Explainability       | Final selections include reasons                             |
| NFR-008 | Data quality         | Invalid records are quarantined                              |
| NFR-009 | Idempotence          | Re-running same source version creates no duplicates         |
| NFR-010 | Graceful degradation | Useful outputs remain possible without raw votes             |
| NFR-011 | Learning value       | Architecture and methods are documented                      |
| NFR-012 | Reviewability        | Reports support human aesthetic review                       |

---

## 14. Physical Data Model

## 14.1 Naming Conventions

| Object Type                | Prefix     |
| -------------------------- | ---------- |
| Raw source table           | `raw_`     |
| Staging table              | `stg_`     |
| Dimension table            | `dim_`     |
| Fact table                 | `fact_`    |
| Cross-reference table      | `xref_`    |
| Bridge table               | `bridge_`  |
| Feature table              | `feature_` |
| Mart table                 | `mart_`    |
| Control table              | `ctl_`     |
| Rejection/quarantine table | `reject_`  |

---

# 15. Core Dimensions

## 15.1 `dim_image`

**Grain:** one logical image or media item.

| Column                | Type            | Description                      |
| --------------------- | --------------- | -------------------------------- |
| `image_sk`            | bigint identity | Internal surrogate key           |
| `source_image_id`     | text            | Stable source image identifier   |
| `source_file_name`    | text            | Source file name                 |
| `media_type`          | text            | photo, video, unknown            |
| `mission_code`        | text            | Example: ART002                  |
| `title`               | text            | Source title                     |
| `description`         | text            | Source description               |
| `photographer`        | text            | Photographer metadata            |
| `location`            | text            | Source location/context          |
| `camera`              | text            | Camera metadata                  |
| `settings`            | text            | Camera settings                  |
| `taken_at_source_tz`  | text            | Original source time string      |
| `taken_at_utc`        | timestamptz     | Normalized timestamp             |
| `distance_from_earth` | numeric         | Distance from Earth if available |
| `distance_to_moon`    | numeric         | Distance to Moon if available    |
| `source_url`          | text            | Source page URL                  |
| `thumbnail_url`       | text            | Thumbnail URL                    |
| `full_image_url`      | text            | Full image URL                   |
| `enabled_flag`        | boolean         | Available for voting/selection   |
| `source_loaded_at`    | timestamptz     | Source load timestamp            |
| `created_at`          | timestamptz     | Warehouse create timestamp       |
| `updated_at`          | timestamptz     | Warehouse update timestamp       |

## 15.2 `dim_voter`

**Grain:** one internal anonymous voter identity.

| Column                  | Type            | Description                                 |
| ----------------------- | --------------- | ------------------------------------------- |
| `voter_sk`              | bigint identity | Internal surrogate voter key                |
| `voter_public_hash`     | text            | Stable non-reversible public analytics hash |
| `first_seen_at`         | timestamptz     | First observed vote                         |
| `last_seen_at`          | timestamptz     | Most recent observed vote                   |
| `vote_session_count`    | integer         | Number of vote sessions                     |
| `source_identity_count` | integer         | Number of source IDs mapped                 |
| `identity_confidence`   | text            | exact, probable, weak, unknown              |
| `created_at`            | timestamptz     | Warehouse create timestamp                  |
| `updated_at`            | timestamptz     | Warehouse update timestamp                  |

## 15.3 `xref_voter_source_identity`

**Grain:** one source voter identifier mapped to one internal voter surrogate.

| Column                     | Type            | Description                              |
| -------------------------- | --------------- | ---------------------------------------- |
| `voter_source_identity_sk` | bigint identity | Internal key                             |
| `voter_sk`                 | bigint          | FK to `dim_voter`                        |
| `source_system`            | text            | Source of voter ID                       |
| `source_voter_id_hash`     | text            | Salted hash of source voter ID           |
| `source_voter_id_raw`      | text nullable   | Restricted; only if explicitly permitted |
| `capture_method`           | text            | export, browser_id, server_log, unknown  |
| `first_seen_at`            | timestamptz     | First seen                               |
| `last_seen_at`             | timestamptz     | Last seen                                |
| `created_at`               | timestamptz     | Warehouse create timestamp               |

## 15.4 `dim_vote_mode`

**Grain:** one voting workflow.

| Column            | Type              | Description                                      |
| ----------------- | ----------------- | ------------------------------------------------ |
| `vote_mode_sk`    | smallint identity | Internal key                                     |
| `vote_mode_code`  | text              | batch_pick_5_of_50, pairwise_elo, category_top_3 |
| `vote_mode_name`  | text              | Display name                                     |
| `choice_set_size` | integer           | 50, 2, category-dependent                        |
| `selection_limit` | integer           | 5, 1, 3                                          |
| `ranking_flag`    | boolean           | True for ranked-category mode                    |
| `description`     | text              | Workflow description                             |
| `created_at`      | timestamptz       | Warehouse create timestamp                       |

## 15.5 `dim_category`

**Grain:** one voting category, mission moment, or curated grouping.

| Column               | Type            | Description                                    |
| -------------------- | --------------- | ---------------------------------------------- |
| `category_sk`        | bigint identity | Internal key                                   |
| `source_category_id` | text            | Source category ID                             |
| `category_name`      | text            | Category display name                          |
| `category_type`      | text            | moment, subject, mission_phase, camera, manual |
| `description`        | text            | Category description                           |
| `created_at`         | timestamptz     | Warehouse create timestamp                     |

## 15.6 `dim_calendar_slot`

**Grain:** one calendar slot.

| Column             | Type              | Description                           |
| ------------------ | ----------------- | ------------------------------------- |
| `calendar_slot_sk` | smallint identity | Internal key                          |
| `calendar_year`    | integer           | 2027                                  |
| `slot_number`      | integer           | 1-13                                  |
| `slot_label`       | text              | January, February, cover, bonus, etc. |
| `slot_type`        | text              | month, cover, bonus                   |
| `display_order`    | integer           | Calendar display order                |
| `created_at`       | timestamptz       | Warehouse create timestamp            |

---

# 16. Core Fact Tables

## 16.1 `fact_vote_session`

**Grain:** one voter interaction with one voting workflow.

| Column                | Type                 | Description                     |
| --------------------- | -------------------- | ------------------------------- |
| `vote_session_sk`     | bigint identity      | Internal key                    |
| `voter_sk`            | bigint               | FK to `dim_voter`               |
| `vote_mode_sk`        | smallint             | FK to `dim_vote_mode`           |
| `category_sk`         | bigint nullable      | FK to `dim_category`            |
| `source_session_id`   | text nullable        | Source session ID, if available |
| `client_timestamp`    | timestamptz nullable | Client-provided timestamp       |
| `server_received_at`  | timestamptz nullable | Server timestamp, if available  |
| `user_agent_hash`     | text nullable        | Hashed user-agent               |
| `user_agent_family`   | text nullable        | Browser/device class, if parsed |
| `source_payload_hash` | text                 | Deduplication hash              |
| `source_loaded_at`    | timestamptz          | Source load timestamp           |
| `created_at`          | timestamptz          | Warehouse create timestamp      |

## 16.2 `fact_batch_ballot`

**Grain:** one random-batch ballot submission.

| Column                    | Type            | Description                |
| ------------------------- | --------------- | -------------------------- |
| `batch_ballot_sk`         | bigint identity | Internal key               |
| `vote_session_sk`         | bigint          | FK to `fact_vote_session`  |
| `voter_sk`                | bigint          | FK to `dim_voter`          |
| `shown_count`             | integer         | Number of images shown     |
| `selected_count`          | integer         | Number of images selected  |
| `expected_shown_count`    | integer         | Expected value, likely 50  |
| `expected_selected_count` | integer         | Expected value, likely 5   |
| `ballot_valid_flag`       | boolean         | Data quality result        |
| `invalid_reason`          | text nullable   | Reason if invalid          |
| `source_payload_hash`     | text            | Deduplication hash         |
| `created_at`              | timestamptz     | Warehouse create timestamp |

## 16.3 `fact_batch_ballot_image`

**Grain:** one image shown inside one batch ballot.

| Column                    | Type             | Description                    |
| ------------------------- | ---------------- | ------------------------------ |
| `batch_ballot_image_sk`   | bigint identity  | Internal key                   |
| `batch_ballot_sk`         | bigint           | FK to `fact_batch_ballot`      |
| `vote_session_sk`         | bigint           | FK to `fact_vote_session`      |
| `voter_sk`                | bigint           | FK to `dim_voter`              |
| `image_sk`                | bigint           | FK to `dim_image`              |
| `display_position`        | integer nullable | Display order if available     |
| `was_shown`               | boolean          | Always true                    |
| `was_selected`            | boolean          | True if selected               |
| `implicit_rejection_flag` | boolean          | True if shown and not selected |
| `created_at`              | timestamptz      | Warehouse create timestamp     |

## 16.4 `fact_pairwise_vote`

**Grain:** one head-to-head comparison.

| Column             | Type            | Description                            |
| ------------------ | --------------- | -------------------------------------- |
| `pairwise_vote_sk` | bigint identity | Internal key                           |
| `vote_session_sk`  | bigint          | FK to `fact_vote_session`              |
| `voter_sk`         | bigint          | FK to `dim_voter`                      |
| `winner_image_sk`  | bigint          | FK to `dim_image`                      |
| `loser_image_sk`   | bigint          | FK to `dim_image`                      |
| `left_image_sk`    | bigint nullable | Display-left image if available        |
| `right_image_sk`   | bigint nullable | Display-right image if available       |
| `winner_position`  | text nullable   | left, right, unknown                   |
| `skipped_flag`     | boolean         | True if skipped, if skip records exist |
| `created_at`       | timestamptz     | Warehouse create timestamp             |

## 16.5 `fact_category_ranking`

**Grain:** one category-ranking submission.

| Column                | Type            | Description                |
| --------------------- | --------------- | -------------------------- |
| `category_ranking_sk` | bigint identity | Internal key               |
| `vote_session_sk`     | bigint          | FK to `fact_vote_session`  |
| `voter_sk`            | bigint          | FK to `dim_voter`          |
| `category_sk`         | bigint          | FK to `dim_category`       |
| `ranked_count`        | integer         | Number of ranked images    |
| `ranking_valid_flag`  | boolean         | Validation result          |
| `invalid_reason`      | text nullable   | Reason if invalid          |
| `created_at`          | timestamptz     | Warehouse create timestamp |

## 16.6 `fact_category_ranking_image`

**Grain:** one ranked image within one category-ranking submission.

| Column                      | Type            | Description                   |
| --------------------------- | --------------- | ----------------------------- |
| `category_ranking_image_sk` | bigint identity | Internal key                  |
| `category_ranking_sk`       | bigint          | FK to `fact_category_ranking` |
| `vote_session_sk`           | bigint          | FK to `fact_vote_session`     |
| `voter_sk`                  | bigint          | FK to `dim_voter`             |
| `category_sk`               | bigint          | FK to `dim_category`          |
| `image_sk`                  | bigint          | FK to `dim_image`             |
| `rank_position`             | integer         | 1, 2, 3                       |
| `borda_score`               | numeric         | Derived score                 |
| `created_at`                | timestamptz     | Warehouse create timestamp    |

---

# 17. Feature Store Tables

## 17.1 `feature_image_embedding`

**Grain:** one image embedding per model version.

| Column                    | Type            | Description         |
| ------------------------- | --------------- | ------------------- |
| `image_embedding_sk`      | bigint identity | Internal key        |
| `image_sk`                | bigint          | FK to `dim_image`   |
| `embedding_model`         | text            | Model family        |
| `embedding_model_version` | text            | Exact model version |
| `embedding_vector`        | vector/array    | Image embedding     |
| `embedding_dimension`     | integer         | Vector length       |
| `source_image_hash`       | text            | Image content hash  |
| `created_at`              | timestamptz     | Create timestamp    |

## 17.2 `feature_description_embedding`

**Grain:** one text embedding per image per model version.

| Column                     | Type            | Description                           |
| -------------------------- | --------------- | ------------------------------------- |
| `description_embedding_sk` | bigint identity | Internal key                          |
| `image_sk`                 | bigint          | FK to `dim_image`                     |
| `embedding_model`          | text            | Model family                          |
| `embedding_model_version`  | text            | Exact model version                   |
| `text_source`              | text            | title, description, metadata_combined |
| `embedding_vector`         | vector/array    | Text embedding                        |
| `embedding_dimension`      | integer         | Vector length                         |
| `source_text_hash`         | text            | Text hash                             |
| `created_at`               | timestamptz     | Create timestamp                      |

## 17.3 `feature_image_visual`

**Grain:** one visual-feature record per image per extraction run.

| Column                    | Type             | Description                 |
| ------------------------- | ---------------- | --------------------------- |
| `image_visual_feature_sk` | bigint identity  | Internal key                |
| `image_sk`                | bigint           | FK to `dim_image`           |
| `feature_run_id`          | text             | Feature extraction run      |
| `orientation`             | text             | landscape, portrait, square |
| `aspect_ratio`            | numeric          | Width / height              |
| `brightness_score`        | numeric          | Derived metric              |
| `contrast_score`          | numeric          | Derived metric              |
| `saturation_score`        | numeric          | Derived metric              |
| `dominant_color_json`     | jsonb            | Palette                     |
| `has_earth_flag`          | boolean nullable | CV/manual flag              |
| `has_moon_flag`           | boolean nullable | CV/manual flag              |
| `has_crew_flag`           | boolean nullable | CV/manual flag              |
| `has_spacecraft_flag`     | boolean nullable | CV/manual flag              |
| `aesthetic_tag_json`      | jsonb            | Tags                        |
| `created_at`              | timestamptz      | Create timestamp            |

## 17.4 `feature_description_text`

**Grain:** one text-feature record per image per extraction run.

| Column                   | Type            | Description                               |
| ------------------------ | --------------- | ----------------------------------------- |
| `description_feature_sk` | bigint identity | Internal key                              |
| `image_sk`               | bigint          | FK to `dim_image`                         |
| `feature_run_id`         | text            | Feature extraction run                    |
| `description_language`   | text            | Language code                             |
| `sentiment_score`        | numeric         | Negative to positive sentiment            |
| `subjectivity_score`     | numeric         | Objective to subjective                   |
| `emotion_json`           | jsonb           | Awe, calm, drama, wonder, isolation, etc. |
| `topic_terms_json`       | jsonb           | Interpretable terms                       |
| `entity_json`            | jsonb           | Earth, Moon, Orion, crew, spacecraft      |
| `mission_phase_label`    | text nullable   | Derived phase                             |
| `month_affinity_json`    | jsonb           | Month suitability components              |
| `cover_affinity_score`   | numeric         | Cover suitability component               |
| `created_at`             | timestamptz     | Create timestamp                          |

## 17.5 `feature_image_cluster`

**Grain:** one image assigned to one cluster for one clustering run.

| Column                 | Type            | Description                     |
| ---------------------- | --------------- | ------------------------------- |
| `image_cluster_sk`     | bigint identity | Internal key                    |
| `image_sk`             | bigint          | FK to `dim_image`               |
| `cluster_run_id`       | text            | Clustering run                  |
| `cluster_type`         | text            | visual, text, multimodal        |
| `cluster_algorithm`    | text            | k-means, HDBSCAN, agglomerative |
| `cluster_id`           | integer         | Cluster label                   |
| `cluster_label`        | text nullable   | Human label                     |
| `distance_to_centroid` | numeric         | Similarity metric               |
| `created_at`           | timestamptz     | Create timestamp                |

---

# 18. Analytical Marts

## 18.1 `mart_image_preference_score`

**Grain:** one image per scoring run.

| Column               | Type        | Description                 |
| -------------------- | ----------- | --------------------------- |
| `score_run_id`       | text        | Scoring run                 |
| `image_sk`           | bigint      | FK to `dim_image`           |
| `shown_count`        | integer     | Batch exposures             |
| `selected_count`     | integer     | Batch selections            |
| `selection_rate`     | numeric     | selected / shown            |
| `elo_score`          | numeric     | Elo score                   |
| `pairwise_wins`      | integer     | Pairwise wins               |
| `pairwise_losses`    | integer     | Pairwise losses             |
| `btl_score`          | numeric     | Bradley-Terry-Luce estimate |
| `borda_score`        | numeric     | Category ranking score      |
| `posterior_mean`     | numeric     | Bayesian score              |
| `posterior_lower`    | numeric     | Credible interval lower     |
| `posterior_upper`    | numeric     | Credible interval upper     |
| `uncertainty_score`  | numeric     | Width or standard error     |
| `polarization_score` | numeric     | Disagreement score          |
| `broad_appeal_score` | numeric     | Consensus-adjusted appeal   |
| `created_at`         | timestamptz | Create timestamp            |

## 18.2 `mart_inter_rater_reliability`

**Grain:** one reliability result per run, vote mode, and optional category.

| Column               | Type             | Description           |
| -------------------- | ---------------- | --------------------- |
| `irr_run_id`         | text             | Reliability run       |
| `vote_mode_sk`       | smallint         | FK to `dim_vote_mode` |
| `category_sk`        | bigint nullable  | FK to `dim_category`  |
| `image_count`        | integer          | Included images       |
| `voter_count`        | integer          | Included voters       |
| `rating_density`     | numeric          | Matrix density        |
| `krippendorff_alpha` | numeric nullable | Agreement metric      |
| `fleiss_kappa`       | numeric nullable | Agreement metric      |
| `kendall_w`          | numeric nullable | Ranking agreement     |
| `spearman_mean`      | numeric nullable | Mean rank correlation |
| `method_notes`       | text             | Assumptions           |
| `created_at`         | timestamptz      | Create timestamp      |

## 18.3 `mart_image_cluster_summary`

**Grain:** one cluster summary per clustering run.

| Column                     | Type    | Description                       |
| -------------------------- | ------- | --------------------------------- |
| `cluster_run_id`           | text    | Cluster run                       |
| `cluster_type`             | text    | visual, text, multimodal          |
| `cluster_id`               | integer | Cluster identifier                |
| `cluster_label`            | text    | Human-readable label              |
| `image_count`              | integer | Number of images                  |
| `top_image_sk`             | bigint  | Best-scoring representative       |
| `mean_preference_score`    | numeric | Average score                     |
| `max_preference_score`     | numeric | Best image score                  |
| `mean_sentiment_score`     | numeric | Average description sentiment     |
| `calendar_candidate_count` | integer | Times used in generated calendars |
| `review_priority`          | text    | high, medium, low                 |
| `notes`                    | text    | Reviewer notes                    |

## 18.4 `mart_cluster_top_images`

**Grain:** one top-ranked image within one cluster.

| Column               | Type    | Description                               |
| -------------------- | ------- | ----------------------------------------- |
| `cluster_run_id`     | text    | Cluster run                               |
| `cluster_type`       | text    | visual, text, multimodal                  |
| `cluster_id`         | integer | Cluster identifier                        |
| `image_sk`           | bigint  | Image key                                 |
| `rank_in_cluster`    | integer | Rank within cluster                       |
| `preference_score`   | numeric | Image appeal score                        |
| `selection_rate`     | numeric | Batch selection rate                      |
| `elo_score`          | numeric | Pairwise score                            |
| `borda_score`        | numeric | Category score                            |
| `diversity_value`    | numeric | Value relative to other images in cluster |
| `recommended_action` | text    | select, alternate, suppress, review       |

## 18.5 `mart_image_calendar_slot_score`

**Grain:** one image scored for one calendar slot.

| Column                    | Type     | Description                    |
| ------------------------- | -------- | ------------------------------ |
| `slot_score_run_id`       | text     | Run identifier                 |
| `image_sk`                | bigint   | Image key                      |
| `calendar_slot_sk`        | smallint | Calendar slot                  |
| `slot_type`               | text     | month, cover, bonus            |
| `slot_label`              | text     | January, February, Cover, etc. |
| `preference_score`        | numeric  | General image appeal           |
| `sentiment_score`         | numeric  | Description sentiment          |
| `visual_mood_score`       | numeric  | Visual tone                    |
| `seasonal_fit_score`      | numeric  | Month fit                      |
| `mission_story_fit_score` | numeric  | Chronological/narrative fit    |
| `typography_space_score`  | numeric  | Cover/layout usability         |
| `print_quality_score`     | numeric  | Technical suitability          |
| `total_slot_score`        | numeric  | Combined score                 |
| `reason`                  | text     | Human-readable explanation     |

## 18.6 `mart_calendar_candidate`

**Grain:** one generated calendar candidate.

| Column                  | Type            | Description               |
| ----------------------- | --------------- | ------------------------- |
| `calendar_candidate_sk` | bigint identity | Internal key              |
| `candidate_run_id`      | text            | Optimization run          |
| `candidate_name`        | text            | Display name              |
| `calendar_year`         | integer         | 2027                      |
| `image_count`           | integer         | 12 or 13                  |
| `objective_score`       | numeric         | Total score               |
| `appeal_score`          | numeric         | Preference component      |
| `diversity_score`       | numeric         | Diversity component       |
| `coverage_score`        | numeric         | Mission/category coverage |
| `month_fit_score`       | numeric         | Month assignment score    |
| `cover_fit_score`       | numeric         | Cover score               |
| `redundancy_penalty`    | numeric         | Similarity penalty        |
| `uncertainty_penalty`   | numeric         | Risk penalty              |
| `created_at`            | timestamptz     | Create timestamp          |

## 18.7 `mart_calendar_candidate_image`

**Grain:** one image assigned to one slot in one candidate calendar.

| Column                        | Type            | Description                     |
| ----------------------------- | --------------- | ------------------------------- |
| `calendar_candidate_image_sk` | bigint identity | Internal key                    |
| `calendar_candidate_sk`       | bigint          | FK to `mart_calendar_candidate` |
| `image_sk`                    | bigint          | FK to `dim_image`               |
| `calendar_slot_sk`            | smallint        | FK to `dim_calendar_slot`       |
| `slot_number`                 | integer         | 1-13                            |
| `slot_label`                  | text            | January, February, cover, bonus |
| `image_score`                 | numeric         | Image preference contribution   |
| `month_fit_score`             | numeric         | Slot fit                        |
| `cover_fit_score`             | numeric         | Cover fit if applicable         |
| `diversity_contribution`      | numeric         | Marginal diversity              |
| `redundancy_contribution`     | numeric         | Similarity penalty              |
| `selection_reason`            | text            | Human-readable explanation      |
| `created_at`                  | timestamptz     | Create timestamp                |

---

# 19. Voter Surrogate Key Design

## 19.1 Principle

The project must maintain anonymous voter continuity without attempting to identify people.

The system will use:

1. Internal surrogate key: `voter_sk`.
2. Public hash: `voter_public_hash`.
3. Source identity cross-reference: `xref_voter_source_identity`.
4. Optional restricted raw source ID field, only if explicitly allowed.

## 19.2 Identity Rules

| Case                                                  | Handling                                                |
| ----------------------------------------------------- | ------------------------------------------------------- |
| Same source voter ID appears repeatedly               | Map to same `voter_sk`                                  |
| Source voter ID missing                               | Create new anonymous `voter_sk` with unknown confidence |
| Same browser/user-agent but different source voter ID | Do not automatically merge                              |
| Same IP hash and same user-agent                      | Do not merge without explicit approved rule             |
| Raw source ID provided                                | Hash immediately                                        |
| Raw source ID not allowed                             | Store only supplied hash                                |
| Multiple vote modes share source voter ID             | Map all to same `voter_sk`                              |
| Multiple vote modes use different IDs                 | Keep separate unless source owner documents linkage     |

## 19.3 Identity Confidence

| Value    | Meaning                        |
| -------- | ------------------------------ |
| exact    | Same source voter ID           |
| probable | Explicit source-system linkage |
| weak     | Heuristic relationship only    |
| unknown  | No stable identity information |

Only `exact` and source-documented `probable` identities should be used in formal inter-rater analysis.

---

# 20. Vote Modeling

## 20.1 Random-Batch Voting

Observed design: voters see 50 random photos and pick 5 favorites. ([Artemis Timeline][1])

Modeling structure:

1. Each shown image is an exposure.
2. Each selected image is a positive outcome.
3. Each shown-but-not-selected image is an implicit negative outcome.
4. Images not shown are missing, not negative.
5. Selection rate must be exposure-adjusted.
6. Low-exposure images require uncertainty adjustment.

Candidate methods:

1. Raw selection rate.
2. Wilson lower bound.
3. Bayesian binomial smoothing.
4. Mixed-effects logistic regression.
5. Voter random effects if raw voter data is available.

## 20.2 Pairwise Voting

Observed design: featured photos go head-to-head, and a running Elo leaderboard ranks the single best image. ([Artemis Timeline][1])

Modeling structure:

1. Preserve winner and loser.
2. Preserve display side if available.
3. Recompute Elo if raw data is available.
4. Estimate Bradley-Terry-Luce scores.
5. Compare pairwise scores to batch selection scores.

Candidate methods:

1. Elo.
2. Bradley-Terry-Luce model.
3. Thurstone-Mosteller model.
4. Bayesian pairwise model.
5. Mixed-effects pairwise model.

## 20.3 Category Ranking

Observed design: voters drag their top 3 photos in each category. ([Artemis Timeline][1])

Modeling structure:

1. Preserve category context.
2. Preserve rank order.
3. Convert rank to Borda score.
4. Preserve exposure set if available.
5. Avoid treating unranked images as rejected unless shown set is known.

Candidate methods:

1. Borda score.
2. Average rank.
3. Plackett-Luce model.
4. Category-specific preference model.
5. Category coverage scoring.

---

# 21. Inter-Rater Reliability

Inter-rater reliability is only fully valid if raw voter-level data is available.

## 21.1 Candidate Metrics

| Metric                 | Use                                                     |
| ---------------------- | ------------------------------------------------------- |
| Krippendorff’s alpha   | General agreement across sparse/incomplete matrices     |
| Fleiss’ kappa          | Agreement among multiple raters on categorical outcomes |
| Kendall’s W            | Agreement among rankings                                |
| Spearman correlation   | Pairwise rank agreement                                 |
| Intraclass correlation | Continuous ratings if any are collected                 |

## 21.2 Batch Rating Matrix

| Condition                    | Rating  |
| ---------------------------- | ------- |
| Image shown and selected     | 1       |
| Image shown and not selected | 0       |
| Image not shown              | missing |

## 21.3 Category Rating Matrix

| Condition            | Rating                        |
| -------------------- | ----------------------------- |
| Rank 1               | 3                             |
| Rank 2               | 2                             |
| Rank 3               | 1                             |
| Shown but not ranked | 0, only if shown set is known |
| Not shown            | missing                       |

## 21.4 Pairwise Matrix

Pairwise votes should be modeled as preference edges rather than forced into a simple rating matrix unless the reliability method explicitly supports pairwise comparisons.

---

# 22. Cluster Analysis

## 22.1 Purpose

Cluster analysis supports:

1. Redundancy control.
2. Collapsible review groups.
3. Top-N-per-group selection.
4. Visual diversity.
5. Description/topic diversity.
6. Mission coverage.
7. Calendar slate balance.
8. Explainability.

The reviewer should be able to see:

1. Top images overall.
2. Top images by cluster.
3. Similar images suppressed by redundancy.
4. Images that are strong but redundant.
5. Images that are weaker individually but valuable for diversity.
6. Clusters underrepresented in the naive leaderboard.

## 22.2 Visual Clustering

Inputs:

1. Image thumbnails.
2. Full images where available.
3. Image embeddings.
4. Visual features.
5. Color palette.
6. Brightness/contrast.
7. Orientation.
8. Subject flags.

Candidate methods:

1. CLIP/SigLIP embeddings.
2. PCA.
3. UMAP.
4. k-means.
5. HDBSCAN.
6. Agglomerative clustering.
7. Cosine similarity.

Outputs:

1. Visual cluster ID.
2. Cluster label.
3. Representative image.
4. Cluster size.
5. Top images in cluster.
6. Redundancy score.
7. Cluster calendar value.

## 22.3 Description Clustering

Inputs:

1. Title.
2. Description.
3. Photographer.
4. Location.
5. Camera.
6. Mission phase.
7. Time/distance metadata.
8. Derived entities.
9. Sentiment.
10. Emotion/tone scores.

Candidate methods:

1. Text embeddings.
2. TF-IDF.
3. Topic modeling.
4. Named entity extraction.
5. Sentiment analysis.
6. Hierarchical clustering.

Outputs:

1. Description cluster ID.
2. Topic label.
3. Top terms.
4. Representative descriptions.
5. Sentiment mean.
6. Month affinity.
7. Cover affinity.
8. Mission narrative value.

## 22.4 Multimodal Clustering

Multimodal clustering combines visual similarity, description similarity, and metadata similarity.

Initial combined similarity:

| Component              | Initial Weight |
| ---------------------- | -------------: |
| Visual similarity      |           0.60 |
| Description similarity |           0.30 |
| Metadata similarity    |           0.10 |

Use cases:

1. Collapse visually similar Earth/Moon images.
2. Preserve visually similar images if mission meaning differs.
3. Identify descriptions that imply strong month fit.
4. Identify visually strong but textually weak images.
5. Identify story-important images that are visually less dramatic.
6. Balance mission narrative with aesthetic quality.

---

# 23. Month and Cover Suitability

## 23.1 Month Suitability

Month suitability should be scored independently from general image preference.

Inputs:

1. Description sentiment.
2. Description topic.
3. Emotional tone.
4. Dominant colors.
5. Brightness.
6. Visual drama.
7. Subject matter.
8. Mission phase.
9. Earth/Moon geometry.
10. Calendar narrative flow.
11. Print/crop suitability.

Example month-fit considerations:

| Month/Slot    | Possible Fit Signals                            |
| ------------- | ----------------------------------------------- |
| January       | Beginning, launch, distance, quiet, renewal     |
| February      | Human element, preparation, closeness           |
| March         | Mission chronology, transition, Earth departure |
| April         | Moon encounter, climax, visual drama            |
| May           | Return, reflection, Earth reentry               |
| Summer months | Brightness, color, expansiveness                |
| Autumn months | Warm tones, distance, reflection                |
| December      | Closing, return, night, awe, completion         |

## 23.2 Cover Suitability

The cover image has a different role from a month image.

Cover suitability should reward:

1. Immediate visual impact.
2. Mission representativeness.
3. Broad appeal.
4. Clear subject.
5. Works at thumbnail size.
6. Works with typography.
7. Strong contrast without clutter.
8. Emotional resonance.
9. Iconic value.
10. Calendar-sales value.

Cover suitability should penalize:

1. Busy composition.
2. Poor typography space.
3. Ambiguous subject.
4. Low resolution.
5. Weak thumbnail performance.
6. Excessive similarity to a month image.

---

# 24. Calendar Optimization

## 24.1 Objective Function

Calendar Utility =

1. image preference score
2. plus voter consensus score
3. plus visual diversity score
4. plus description diversity score
5. plus mission phase coverage score
6. plus month fit score
7. plus cover fit score
8. plus cluster coverage score
9. minus visual redundancy penalty
10. minus description redundancy penalty
11. minus uncertainty penalty
12. minus overconcentration penalty

## 24.2 Constraints

| Constraint             | Description                                                           |
| ---------------------- | --------------------------------------------------------------------- |
| Image count            | 12 or 13 images                                                       |
| Cover handling         | Cover may be separate or included as one of 13                        |
| Cluster concentration  | Limit images from same visual/text cluster                            |
| Mission coverage       | Avoid overconcentration in one mission phase                          |
| Subject coverage       | Balance Earth, Moon, spacecraft, crew, interior/exterior if available |
| Camera/source coverage | Avoid unnecessary overreliance on one source                          |
| Technical quality      | Exclude poor-resolution or poor-crop images                           |
| Confidence floor       | Avoid low-confidence images unless deliberately selected              |
| Redundancy ceiling     | Suppress near-duplicate images                                        |
| Month fit              | Assign images to appropriate slots                                    |
| Review override        | Allow human review to override model output with documented reason    |

## 24.3 Candidate Methods

1. Naive top-N baseline.
2. Greedy diversity-aware selection.
3. Maximum marginal relevance.
4. Integer programming.
5. Determinantal point process.
6. Simulated annealing.
7. Human-curated comparison set.

## 24.4 Required Baselines

| Baseline                       | Purpose                         |
| ------------------------------ | ------------------------------- |
| Top 13 by selection rate       | Shows naive batch-vote result   |
| Top 13 by Elo                  | Shows naive pairwise result     |
| Top 13 by category score       | Shows naive category result     |
| Top representative per cluster | Shows diversity-first result    |
| Optimized slate                | Shows combined objective result |

---

# 25. Archive and Refresh Design

## 25.1 Archive Principle

Every source snapshot should be stored immutably.

Each archived file should have:

1. Source name.
2. Source URL.
3. Retrieval timestamp.
4. Content hash.
5. File size.
6. Load run ID.
7. Parser version.
8. Validation result.

## 25.2 Source Types

| Source Type          | Examples                            |
| -------------------- | ----------------------------------- |
| Main site snapshot   | ArtemisTimeline page                |
| Voting page snapshot | Vote page                           |
| Image manifest       | Public image metadata / manifest    |
| Leaderboard summary  | Overall, Elo, category leaderboards |
| Raw vote export      | If provided by site owner           |
| Image files          | Thumbnails or full images           |
| Derived files        | Embeddings, clusters, model outputs |

## 25.3 Refresh Modes

| Mode                  | Purpose                           |
| --------------------- | --------------------------------- |
| `snapshot-refresh`    | Download and archive source pages |
| `metadata-refresh`    | Parse and load image metadata     |
| `leaderboard-refresh` | Capture aggregate vote summaries  |
| `vote-refresh`        | Load raw vote exports             |
| `feature-refresh`     | Recompute image/text features     |
| `cluster-refresh`     | Rebuild clusters                  |
| `score-refresh`       | Recompute preference scores       |
| `calendar-refresh`    | Regenerate calendar candidates    |
| `publish-report`      | Build reports                     |

## 25.4 Change Detection

The pipeline should detect:

1. New image records.
2. Removed image records.
3. Changed metadata.
4. Changed descriptions.
5. Changed leaderboard scores.
6. New vote exports.
7. Changed categories.
8. Schema drift.
9. Parser failures.
10. Image file changes.

---

# 26. Data Quality Plan

## 26.1 Validation Rules

| Rule ID | Rule                                                          |
| ------- | ------------------------------------------------------------- |
| DQ-001  | Every vote image ID must map to `dim_image`                   |
| DQ-002  | Batch selected images must be a subset of shown images        |
| DQ-003  | Batch selected count must not exceed selection limit          |
| DQ-004  | Pairwise winner and loser must be different images            |
| DQ-005  | Category rank positions must be unique within one submission  |
| DQ-006  | Duplicate payloads must be detected by hash                   |
| DQ-007  | Missing voter IDs must be assigned anonymous surrogate keys   |
| DQ-008  | Invalid rows must be quarantined                              |
| DQ-009  | Timestamp values must be plausible                            |
| DQ-010  | Images below exposure threshold must be marked uncertain      |
| DQ-011  | Cluster run must assign every eligible image                  |
| DQ-012  | Calendar candidate must contain no duplicate images           |
| DQ-013  | Calendar candidate must satisfy slot count                    |
| DQ-014  | Month assignment must assign exactly one image per month slot |
| DQ-015  | Cover assignment must satisfy cover constraints               |

## 26.2 Quarantine Tables

| Table                       | Purpose                        |
| --------------------------- | ------------------------------ |
| `reject_image_metadata`     | Invalid image metadata         |
| `reject_batch_ballot`       | Invalid batch ballots          |
| `reject_pairwise_vote`      | Invalid pairwise votes         |
| `reject_category_ranking`   | Invalid category rankings      |
| `reject_identity_mapping`   | Invalid voter identity records |
| `reject_cluster_assignment` | Invalid clustering outputs     |
| `reject_calendar_candidate` | Invalid generated slates       |

---

# 27. Privacy and Ethics

## 27.1 Privacy Principle

The system should not identify voters.

The system should preserve anonymous continuity only to support valid statistical analysis.

## 27.2 Data Minimization

| Data Element         | Recommendation                                                          |
| -------------------- | ----------------------------------------------------------------------- |
| Raw voter ID         | Avoid storing, or store only in restricted access if explicitly allowed |
| Source voter ID hash | Store salted hash                                                       |
| User-agent           | Hash or reduce to coarse family                                         |
| IP address           | Prefer exclusion                                                        |
| Timestamp            | Keep for analysis but do not publish voter-level behavior               |
| Vote records         | Use for aggregate modeling                                              |
| Public outputs       | Do not expose voter-level rows                                          |

## 27.3 Publication Boundary

Public reports may include:

1. Aggregate counts.
2. Image-level scores.
3. Cluster summaries.
4. Agreement metrics.
5. Calendar candidate scores.
6. Selection explanations.
7. Methodology notes.

Public reports must not include:

1. Raw voter IDs.
2. Individual voter histories.
3. Full user-agent strings.
4. IP addresses.
5. Re-identification analysis.
6. Any claim implying known personal identity.

---

# 28. Run Control

## 28.1 `ctl_data_load_run`

| Column             | Type        | Description              |
| ------------------ | ----------- | ------------------------ |
| `load_run_id`      | text        | Unique load run          |
| `source_name`      | text        | Source system            |
| `source_file_path` | text        | Raw file path            |
| `source_file_hash` | text        | File checksum            |
| `loaded_at`        | timestamptz | Load timestamp           |
| `row_count`        | integer     | Loaded rows              |
| `reject_count`     | integer     | Rejected rows            |
| `status`           | text        | success, partial, failed |
| `notes`            | text        | Load notes               |

## 28.2 `ctl_model_run`

| Column               | Type        | Description                       |
| -------------------- | ----------- | --------------------------------- |
| `model_run_id`       | text        | Unique model run                  |
| `model_type`         | text        | scoring, clustering, optimization |
| `input_load_run_ids` | text[]      | Source runs                       |
| `parameter_json`     | jsonb       | Parameters                        |
| `started_at`         | timestamptz | Start time                        |
| `completed_at`       | timestamptz | End time                          |
| `status`             | text        | success, partial, failed          |
| `notes`              | text        | Run notes                         |

## 28.3 `ctl_source_manifest`

| Column               | Type            | Description                                    |
| -------------------- | --------------- | ---------------------------------------------- |
| `source_manifest_sk` | bigint identity | Internal key                                   |
| `source_name`        | text            | Source name                                    |
| `source_type`        | text            | page, manifest, leaderboard, raw_export, image |
| `source_url`         | text            | URL or source path                             |
| `expected_format`    | text            | html, json, csv, js, image                     |
| `refresh_frequency`  | text            | manual, daily, weekly                          |
| `active_flag`        | boolean         | Whether source is active                       |
| `last_checked_at`    | timestamptz     | Last check                                     |
| `last_changed_at`    | timestamptz     | Last detected change                           |
| `notes`              | text            | Source notes                                   |

---

# 29. Reports

## 29.1 Image Scoring Report

Must include:

1. Top images by selection rate.
2. Top images by Elo.
3. Top images by Bradley-Terry-Luce score.
4. Top images by category score.
5. High-consensus images.
6. Polarizing images.
7. High-uncertainty images.
8. Underexposed promising images.
9. Redundant image groups.
10. Images suppressed due to redundancy.

## 29.2 Cluster Review Report

Must include:

1. Visual clusters.
2. Description clusters.
3. Multimodal clusters.
4. Top images per cluster.
5. Representative images.
6. Cluster labels.
7. Cluster summary descriptions.
8. Cluster sentiment summaries.
9. Cluster calendar usefulness.
10. Cluster-level review notes.

## 29.3 Inter-Rater Report

If raw votes are available, must include:

1. Voter count.
2. Vote count.
3. Rating matrix density.
4. Krippendorff’s alpha.
5. Fleiss’ kappa where applicable.
6. Kendall’s W for rankings.
7. Agreement by vote mode.
8. Agreement by category.
9. Agreement by cluster.
10. Sparse-data limitations.

## 29.4 Calendar Candidate Report

Must include:

1. Candidate calendar slate.
2. Month assignment.
3. Cover assignment.
4. Selected images.
5. Selection reason per image.
6. Preference score.
7. Diversity contribution.
8. Redundancy penalty.
9. Month suitability score.
10. Cover suitability score.
11. Cluster coverage.
12. Mission coverage.
13. Comparison to naive top-N baselines.
14. Human-review notes.

## 29.5 Learning Report

Must include:

1. Architecture explanation.
2. Pipeline walkthrough.
3. Data model explanation.
4. Vote modeling explanation.
5. Clustering explanation.
6. Reliability metric explanation.
7. Calendar optimization explanation.
8. Lessons learned.
9. Mistakes and corrections.
10. Reusable patterns.

---

# 30. Documentation Plan

## 30.1 Required Documents

| Document                                 | Purpose                  |
| ---------------------------------------- | ------------------------ |
| `docs/00_project_overview.md`            | Project introduction     |
| `docs/01_pdr.md`                         | Physical design document |
| `docs/02_data_sources.md`                | Source documentation     |
| `docs/03_pipeline_architecture.md`       | Pipeline architecture    |
| `docs/04_warehouse_design.md`            | Data model               |
| `docs/05_vote_modeling.md`               | Vote modeling methods    |
| `docs/06_voter_surrogate_keys.md`        | Voter identity strategy  |
| `docs/07_image_clustering.md`            | Visual clustering        |
| `docs/08_description_clustering.md`      | Text clustering          |
| `docs/09_multimodal_clustering.md`       | Combined clustering      |
| `docs/10_inter_rater_reliability.md`     | Agreement metrics        |
| `docs/11_calendar_optimization.md`       | Slate selection          |
| `docs/12_month_and_cover_scoring.md`     | Slot scoring             |
| `docs/13_privacy_and_ethics.md`          | Privacy rules            |
| `docs/14_lessons_learned.md`             | Learning registry        |
| `docs/15_methodology_for_publication.md` | Public explanation       |

## 30.2 Lessons Learned Registry

Each lesson should include:

1. Problem.
2. Why it matters.
3. Design choice.
4. Alternatives considered.
5. Implementation notes.
6. Validation method.
7. What was learned.
8. Reusable pattern.

Initial lessons:

| Lesson | Topic                                   |
| ------ | --------------------------------------- |
| 001    | Raw archive pattern                     |
| 002    | Surrogate voter keys                    |
| 003    | Why top-N is not enough                 |
| 004    | Exposure-adjusted voting                |
| 005    | Krippendorff’s alpha with sparse votes  |
| 006    | Bradley-Terry-Luce for image comparison |
| 007    | Image embeddings for redundancy         |
| 008    | Text embeddings for descriptions        |
| 009    | Multimodal clustering                   |
| 010    | Calendar as portfolio optimization      |
| 011    | Month fit scoring                       |
| 012    | Reproducible model runs                 |
| 013    | Schema drift and source drift           |
| 014    | Explainable candidate selection         |
| 015    | Aggregate-only fallback design          |

---

# 31. Pipeline Explorer Requirement

A later phase should include a simple static Pipeline Explorer.

JobClass includes a Pipeline Explorer release with an interactive graph showing nodes and edges across the pipeline, educational walkthroughs, search/filter controls, and cross-links to lesson pages. ([GitHub][3])

The Artemis project Pipeline Explorer should show:

1. Source pages.
2. Raw archive.
3. Staging tables.
4. Core dimensions.
5. Core facts.
6. Feature tables.
7. Clustering runs.
8. Preference models.
9. Reliability models.
10. Calendar optimization.
11. Reports.
12. Lessons.

Minimum version:

1. Static graph.
2. Node descriptions.
3. Pipeline stage lanes.
4. Links to relevant docs.
5. Links to lesson pages.
6. Run-status summary.

---

# 32. Implementation Phases

## 32.1 Phase 0: PDR Closure

Deliverables:

1. Approved PDR.
2. Approved problem framing.
3. Approved data model.
4. Approved privacy boundary.
5. Approved raw data request email.
6. Decision on 12 vs 13 image target.
7. Decision on aggregate-only prototype.

Exit criteria:

1. PDR comments resolved.
2. Open questions assigned.
3. Data access request sent.
4. Repository skeleton approved.

## 32.2 Phase 1: Public Data Prototype

Deliverables:

1. Source manifest.
2. Raw archive path.
3. Main page snapshot.
4. Voting page snapshot.
5. Public metadata ingestion.
6. Public leaderboard ingestion if available.
7. Basic image dimension.
8. Basic report.

Exit criteria:

1. Source snapshots archived.
2. Image metadata loaded.
3. Public data report generated.
4. Missing data documented.

## 32.3 Phase 1A: JobClass Pattern Adaptation

Deliverables:

1. Extract module.
2. Archive module.
3. Parse module.
4. Load module.
5. Validate module.
6. Observe module.
7. Run manifest.
8. First test suite.

Exit criteria:

1. Pipeline can be re-run without duplicates.
2. Load run is recorded.
3. Source hashes are recorded.
4. Validation report is generated.

## 32.4 Phase 2: Raw Vote Ingestion

Deliverables:

1. Raw vote archive.
2. Voter surrogate-key mapping.
3. Batch ballot fact tables.
4. Pairwise vote fact tables.
5. Category ranking fact tables.
6. Vote data quality report.

Exit criteria:

1. Every vote maps to a voter surrogate key.
2. Every vote image maps to an image key.
3. Invalid records are quarantined.
4. Exposure matrix can be produced.

## 32.5 Phase 2A: Clustering Foundation

Deliverables:

1. Image embeddings.
2. Description embeddings.
3. Visual clusters.
4. Text clusters.
5. Multimodal clusters.
6. Cluster top-image report.

Exit criteria:

1. Every eligible image has embeddings.
2. Every eligible image has cluster assignments.
3. Clusters are reproducible by run ID.
4. Cluster report is reviewable.

## 32.6 Phase 3: Statistical Modeling

Deliverables:

1. Exposure-adjusted image scores.
2. Elo recomputation if raw pairwise data is available.
3. Bradley-Terry-Luce scores.
4. Borda/category scores.
5. Uncertainty intervals.
6. Krippendorff’s alpha and related metrics if supported.

Exit criteria:

1. Scoring model documented.
2. Reliability assumptions documented.
3. Model outputs reproducible by run ID.
4. Aggregate-only limitations documented.

## 32.7 Phase 4: Calendar Optimization

Deliverables:

1. Calendar objective function.
2. Month suitability model.
3. Cover suitability model.
4. Candidate generation.
5. Candidate comparison report.
6. Baseline comparison.

Exit criteria:

1. At least 5 candidate calendars generated.
2. Naive top-N baselines generated.
3. Optimized candidates compared against baselines.
4. Selection reasons generated for every image.

## 32.8 Phase 5: Learning and Publication Package

Deliverables:

1. Final recommended slate.
2. Alternate slates.
3. Image scoring appendix.
4. Cluster appendix.
5. Reliability appendix.
6. Architecture documentation.
7. Lessons learned registry.
8. Public methodology report.

Exit criteria:

1. Final slate approved for review.
2. Known limitations documented.
3. Lessons learned complete.
4. Public-facing summary ready.

---

# 33. Acceptance Criteria

## 33.1 PDR Acceptance Criteria

| ID         | Criterion                                            |
| ---------- | ---------------------------------------------------- |
| AC-PDR-001 | Data sources are identified                          |
| AC-PDR-002 | Raw voter data is explicitly marked as open question |
| AC-PDR-003 | Voter surrogate-key design is included               |
| AC-PDR-004 | Batch, pairwise, and category vote modes are modeled |
| AC-PDR-005 | Aggregate-only fallback is defined                   |
| AC-PDR-006 | Privacy handling is defined                          |
| AC-PDR-007 | Visual clustering is defined                         |
| AC-PDR-008 | Description clustering is defined                    |
| AC-PDR-009 | Multimodal clustering is defined                     |
| AC-PDR-010 | Month and cover scoring are defined                  |
| AC-PDR-011 | Calendar optimization objective is defined           |
| AC-PDR-012 | JobClass-style pipeline architecture is incorporated |
| AC-PDR-013 | Archive and refresh process is defined               |
| AC-PDR-014 | Lessons learned are included as deliverables         |
| AC-PDR-015 | Risks and dependencies are documented                |
| AC-PDR-016 | Implementation phases are defined                    |

## 33.2 Technical Acceptance Criteria

| ID       | Criterion                                        |
| -------- | ------------------------------------------------ |
| AC-T-001 | Image metadata loads into `dim_image`            |
| AC-T-002 | Every image has a stable `image_sk`              |
| AC-T-003 | Every voter record maps to a `voter_sk`          |
| AC-T-004 | Batch ballots preserve shown and selected images |
| AC-T-005 | Pairwise votes preserve winner and loser         |
| AC-T-006 | Category rankings preserve rank order            |
| AC-T-007 | Invalid records are quarantined                  |
| AC-T-008 | Score runs are reproducible                      |
| AC-T-009 | Cluster runs are reproducible                    |
| AC-T-010 | Calendar candidates are reproducible             |
| AC-T-011 | Month scores are produced for candidate images   |
| AC-T-012 | Cover scores are produced for candidate images   |
| AC-T-013 | Reports show top images within clusters          |
| AC-T-014 | Final report explains each selected image        |
| AC-T-015 | Lessons learned are updated during development   |

---

# 34. Risks

| Risk                                     | Severity   | Mitigation                                     |
| ---------------------------------------- | ---------- | ---------------------------------------------- |
| Raw voter data unavailable               | High       | Build aggregate-only fallback                  |
| Voter IDs unstable                       | Medium     | Use identity confidence levels                 |
| Sparse vote coverage                     | High       | Use Bayesian smoothing and uncertainty scoring |
| Images visually redundant                | Medium     | Use embeddings and cluster constraints         |
| Descriptions inconsistent or sparse      | Medium     | Combine text with metadata and visual signals  |
| Leaderboard biased by exposure imbalance | High       | Use exposure-adjusted metrics                  |
| Category exposure unknown                | Medium     | Avoid treating unranked images as rejected     |
| Privacy concern                          | High       | Hash identifiers and avoid PII                 |
| Image IDs inconsistent across modes      | Medium     | Build image ID crosswalk                       |
| Calendar objective too subjective        | Medium     | Compare multiple objective variants            |
| Overfitting to voters                    | Medium     | Human review and holdout validation            |
| Source pages change structure            | Medium     | Archive raw snapshots and detect drift         |
| Image download scale grows               | Low/Medium | Cache, hash, and process incrementally         |
| Month scoring too artificial             | Medium     | Keep explanations and allow human override     |
| Learning docs fall behind                | Medium     | Include documentation tasks in phase exits     |

---

# 35. Decision Log

| Decision ID | Decision                                         | Status   |
| ----------- | ------------------------------------------------ | -------- |
| D-001       | Use JobClass-style layered architecture          | Proposed |
| D-002       | Use surrogate voter keys for all analytics       | Proposed |
| D-003       | Preserve raw vote-event structure                | Proposed |
| D-004       | Support both 12- and 13-image calendars          | Proposed |
| D-005       | Use image embeddings for visual clustering       | Proposed |
| D-006       | Use text embeddings for description clustering   | Proposed |
| D-007       | Use multimodal clustering for review groups      | Proposed |
| D-008       | Use aggregate-only mode if raw votes unavailable | Proposed |
| D-009       | Score cover suitability separately               | Proposed |
| D-010       | Track lessons learned as first-class output      | Proposed |
| D-011       | Require PDR approval before implementation       | Proposed |

---

# 36. Open Questions

## 36.1 Data Access Questions

1. Can anonymized raw random-batch ballots be shared?
2. Can anonymized raw pairwise votes be shared?
3. Can anonymized raw category rankings be shared?
4. Are voter identifiers stable across voting modes?
5. Are voter identifiers browser-local or server-generated?
6. Are timestamps available for each vote?
7. Are display positions stored for random-batch voting?
8. Are skipped pairwise comparisons stored?
9. For category rankings, is the full shown set available or only the top 3?
10. Are user-agent strings stored?
11. Are IP addresses stored?
12. Can IP addresses be excluded entirely?
13. Is there a stable image manifest?
14. Are all 7,000+ voting images available for metadata download?
15. Are all images available for embedding generation?
16. Is public publication of aggregate analysis acceptable?
17. What credit line should be used?

## 36.2 Product Questions

1. Is the target calendar 12 images, 13 images, or 13 plus cover?
2. Should the cover be optimized separately?
3. Should the calendar emphasize mission chronology?
4. Should each month correspond to a mission phase?
5. Should voter preference outweigh mission coverage?
6. Should the final selection include human override?
7. Should category winners be guaranteed representation?
8. Should technical image quality be manually reviewed?
9. Should crew images and Earth/Moon images be balanced?
10. Should there be separate public and reviewer reports?

## 36.3 Modeling Questions

1. Which embedding model should be used for image similarity?
2. Which embedding model should be used for description similarity?
3. How should visual and text similarity be weighted?
4. How many clusters should be used for review?
5. Should HDBSCAN or k-means be the default clustering method?
6. How should month sentiment be calibrated?
7. Should cover suitability be model-based, human-reviewed, or both?
8. How should uncertainty affect calendar selection?
9. How many candidate calendars should be generated?
10. How should human override decisions be documented?

---

# 37. Data Request Email Requirements

The email to the site owner should request:

1. An anonymized export of random-batch vote records.
2. An anonymized export of head-to-head pairwise votes.
3. An anonymized export of category ranking records.
4. A stable image metadata file.
5. A stable image manifest.
6. Documentation of voter ID behavior.
7. Confirmation of whether voter IDs are stable across vote modes.
8. Confirmation of whether display position is stored.
9. Confirmation of whether category exposure sets are stored.
10. Confirmation of what fields may be used publicly.
11. Permission to publish aggregate findings.
12. Preferred attribution language.

The email should promise:

1. No attempt to identify voters.
2. Use of anonymous surrogate voter keys.
3. Aggregate-only reporting.
4. No publication of individual voter histories.
5. No publication of user-agent or IP information.
6. Sharing of findings back to the site owner.
7. Clear documentation of methods.
8. Respect for publication constraints.

---

# 38. PDR Review Checklist

| Area                       | Status |
| -------------------------- | ------ |
| Problem definition         | Ready  |
| Source summary             | Ready  |
| Raw vote availability      | Open   |
| Voter surrogate design     | Ready  |
| Physical data model        | Ready  |
| Archive and refresh design | Ready  |
| Privacy model              | Ready  |
| Statistical approach       | Ready  |
| Aggregate fallback         | Ready  |
| Image clustering           | Ready  |
| Description clustering     | Ready  |
| Multimodal clustering      | Ready  |
| Month suitability          | Ready  |
| Cover suitability          | Ready  |
| Calendar optimization      | Ready  |
| Data quality               | Ready  |
| Lessons learned            | Ready  |
| Acceptance criteria        | Ready  |
| Risks                      | Ready  |
| Implementation phases      | Ready  |

---

# 39. Recommended PDR Outcome

Approve the design to proceed into Phase 0 closure and Phase 1 public-data prototyping.

The major unresolved dependency is raw voter data access. If raw voter data is granted, the project can support true inter-rater analysis using voter-level matrices and agreement metrics such as Krippendorff’s alpha. If raw voter data is not granted, the project remains viable as an aggregate preference, clustering, and calendar-optimization project, but claims about inter-rater reliability must be limited.

---

# 40. Summary

This design creates a defensible data platform for selecting an Artemis II calendar collection. It preserves image metadata, vote structure, anonymous voter continuity, preference signals, visual similarity, description similarity, sentiment, mission context, calendar slot suitability, and optimization outputs.

The central design choice is to maintain the natural grain of all source data and avoid collapsing votes into a single score too early. The system will support raw-vote analysis if data is provided, while still producing useful aggregate-only analysis if raw voter data is not available.

The final project should answer:

**Which 12 or 13 Artemis II images form the strongest calendar collection, and why is that collection better than simply choosing the top-ranked individual images?**

[1]: https://artemistimeline.com/vote "Artemis II Photo Voter"
[2]: https://artemistimeline.com/ "ARTEMIS II PHOTO TIMELINE"
[3]: https://github.com/bonjohen/jobclass "GitHub - bonjohen/jobclass: Labor market occupation data pipeline — ingests SOC, OEWS, O*NET, and BLS Projections into a layered analytical warehouse · GitHub"
