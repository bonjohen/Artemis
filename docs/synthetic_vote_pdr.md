# Design Document

## Representative Voter Data Simulation with Intentional Bias Detection

**Document status:** Companion design document
**Project:** Artemis II 2027 Calendar Image Selection
**Purpose:** Define how to create synthetic representative voter data with known intentional biases so the project’s scoring, clustering, inter-rater, and calendar-selection processes can identify and explain those biases.
**Calendar target:** 13 images total: **1 cover image plus 12 monthly images**.

---

## 1. Purpose

This document describes a synthetic voter-data generation process for testing the Artemis II calendar image-selection platform.

The goal is to create realistic representative voter data with known embedded bias patterns. These biases should be detectable by the project’s data quality checks, scoring models, clustering analysis, inter-rater analysis, and calendar optimization process.

The synthetic data should help answer:

1. Can the system detect biased voter behavior?
2. Can the system distinguish broad appeal from subgroup preference?
3. Can the system identify over-selection of similar images?
4. Can the system detect position bias?
5. Can the system detect cluster bias?
6. Can the system identify coordinated voting behavior?
7. Can the system avoid selecting a calendar slate that is merely a biased top-N list?
8. Can the system select a better **cover plus 12 monthly images** using preference, diversity, month fit, and redundancy controls?

---

## 2. Design Principle

Synthetic data should be generated with **known ground truth**.

The project should know, before modeling:

1. Which voters are neutral.
2. Which voters are biased.
3. Which images are objectively assigned higher latent appeal.
4. Which image clusters are being over-favored.
5. Which descriptions are being over-favored.
6. Which voters exhibit position bias.
7. Which voters exhibit category bias.
8. Which voters are low-information or random.
9. Which voters are coordinated.
10. Which images are intended to be strong cover candidates.
11. Which images are intended to be strong monthly candidates.

The analysis pipeline should not be given these labels during scoring. The labels should be used only afterward to evaluate whether the system correctly detected the planted patterns.

---

## 3. Synthetic Data Goals

The synthetic voter dataset should support:

1. Batch voting simulation.
2. Pairwise voting simulation.
3. Category ranking simulation.
4. Voter surrogate-key testing.
5. Exposure-adjusted scoring validation.
6. Cluster-bias detection.
7. Position-bias detection.
8. Sentiment-bias detection.
9. Month-fit testing.
10. Cover-fit testing.
11. Coordinated-voter detection.
12. Inter-rater reliability testing.
13. Calendar slate optimization testing.

---

## 4. Synthetic Data Scope

## 4.1 In Scope

The synthetic data generator should create:

1. Synthetic voters.
2. Synthetic voter segments.
3. Synthetic image preference profiles.
4. Synthetic batch ballots.
5. Synthetic pairwise votes.
6. Synthetic category rankings.
7. Synthetic voter identity records.
8. Synthetic vote sessions.
9. Synthetic image exposure records.
10. Synthetic bias labels.
11. Synthetic ground-truth image appeal scores.
12. Synthetic calendar-slot suitability scores.
13. Synthetic cover suitability scores.
14. Synthetic cluster preferences.

## 4.2 Out of Scope

The synthetic data generator does not need to create:

1. New synthetic images.
2. Synthetic image files.
3. Fake real-person identities.
4. Public-facing voter profiles.
5. Production voting infrastructure.
6. A real-time voting simulator.

---

## 5. Synthetic Data Sources

The synthetic voter generator should use the real image universe where possible.

Inputs:

1. `dim_image`
2. `feature_image_cluster`
3. `feature_description_text`
4. `feature_description_embedding`
5. `feature_image_visual`
6. `mart_image_calendar_slot_score`
7. Existing public leaderboard aggregates, if available
8. Manually assigned image test labels, if needed

Synthetic outputs should be loaded into parallel tables or clearly marked synthetic runs.

Recommended pattern:

| Real Table                     | Synthetic Equivalent                                     |
| ------------------------------ | -------------------------------------------------------- |
| `dim_voter`                    | `synthetic_dim_voter` or `dim_voter` with synthetic flag |
| `fact_vote_session`            | synthetic sessions marked by run ID                      |
| `fact_batch_ballot`            | synthetic ballots marked by run ID                       |
| `fact_pairwise_vote`           | synthetic pairwise votes marked by run ID                |
| `fact_category_ranking`        | synthetic rankings marked by run ID                      |
| `mart_image_preference_score`  | synthetic scoring runs                                   |
| `mart_inter_rater_reliability` | synthetic reliability runs                               |

Preferred approach:

Use the same production tables with these fields:

| Column                   | Purpose                   |
| ------------------------ | ------------------------- |
| `synthetic_flag`         | True for generated data   |
| `synthetic_run_id`       | Identifies generation run |
| `synthetic_profile_code` | Voter/image bias profile  |
| `ground_truth_json`      | Restricted test metadata  |

---

## 6. Synthetic Voter Segments

The generator should create a mixture of voter types.

## 6.1 Neutral Voters

Neutral voters approximate reasonable general audience behavior.

Behavior:

1. Prefer high-appeal images.
2. Slightly prefer visually dramatic images.
3. Mildly prefer strong descriptions.
4. No strong cluster bias.
5. No intentional manipulation.
6. Some randomness.

Expected detection:

1. Broad agreement with latent image quality.
2. Moderate inter-rater reliability.
3. No extreme anomaly patterns.

## 6.2 Visual Drama Voters

These voters heavily prefer dramatic Earth/Moon/space images.

Behavior:

1. Strong preference for visually dramatic images.
2. Strong preference for high contrast.
3. Strong preference for images with Earth or Moon.
4. Weak concern for mission chronology.
5. Weak concern for description quality.

Expected detection:

1. Preference concentration in visual clusters.
2. High scores for visually dramatic groups.
3. Possible over-selection of redundant images.

## 6.3 Mission Story Voters

These voters prefer images with strong narrative or mission-context descriptions.

Behavior:

1. Strong preference for historically meaningful images.
2. Strong preference for specific mission phases.
3. Strong preference for images with rich descriptions.
4. Lower dependence on visual drama.

Expected detection:

1. Higher correlation with description clusters than visual clusters.
2. Stronger description-sentiment/topic signal.
3. Support for images that may not be visually dominant.

## 6.4 Crew-Focused Voters

These voters prefer crew images.

Behavior:

1. Prefer images with astronauts or human context.
2. Prefer interior/cabin images.
3. Prefer emotionally warm descriptions.
4. May under-rank pure Earth/Moon exterior images.

Expected detection:

1. Cluster-level preference for crew/human categories.
2. Different top-N list from visual-drama voters.
3. Possible higher month-fit scores for human-interest months.

## 6.5 Technical Voters

These voters prefer technically interesting mission images.

Behavior:

1. Prefer spacecraft, instruments, camera metadata, technical context.
2. Prefer images with precise descriptions.
3. Prefer unusual mission moments.
4. Less sensitive to conventional beauty.

Expected detection:

1. Topic-cluster bias toward spacecraft/technical descriptions.
2. Selection of lower-mainstream but high-context images.
3. Increased polarization for technical images.

## 6.6 Cover-Image Voters

These voters behave as if selecting a cover, not monthly images.

Behavior:

1. Prefer iconic images.
2. Prefer strong thumbnail impact.
3. Prefer simple composition.
4. Prefer strong typography space.
5. Prefer broad mission symbolism.

Expected detection:

1. High correlation with cover suitability score.
2. Different ranking than month-fit voters.
3. Strong top-heavy preference distribution.

## 6.7 Month-Fit Voters

These voters choose images as if placing them into calendar months.

Behavior:

1. Prefer images that match season, mood, and narrative flow.
2. Value variety.
3. Avoid redundancy.
4. Favor softer or transitional images for some months.
5. May not always choose the most dramatic image.

Expected detection:

1. Higher diversity across clusters.
2. Higher month-slot suitability.
3. Lower raw leaderboard concentration.

## 6.8 Position-Biased Voters

These voters are biased by display position.

Behavior:

1. Prefer first few images in a batch.
2. Prefer left image in pairwise voting.
3. Prefer rank options near top of page.
4. Preference partly independent of image quality.

Expected detection:

1. Selection probability correlated with display position.
2. Pairwise winner position imbalance.
3. Weak correlation with image quality.
4. Data quality warning.

## 6.9 Fatigued Voters

These voters become less careful over time.

Behavior:

1. Early votes align with preferences.
2. Later votes become random or position-biased.
3. Pairwise choices become noisier.
4. Batch selections become less consistent.

Expected detection:

1. Session-order effects.
2. Declining consistency.
3. Higher entropy in later votes.
4. Lower intra-voter agreement.

## 6.10 Random Voters

These voters vote randomly.

Behavior:

1. No stable preference.
2. No meaningful cluster bias.
3. No correlation with image quality.
4. No reliable pattern except randomness.

Expected detection:

1. Low consistency.
2. Low contribution to agreement.
3. High entropy.
4. Weak model fit.

## 6.11 Contrarian Voters

These voters avoid popular images.

Behavior:

1. Prefer lower-appeal images.
2. Avoid visually obvious winners.
3. May select obscure clusters.
4. May reduce apparent consensus.

Expected detection:

1. Negative correlation with broad preference.
2. Increased polarization.
3. Possible subgroup pattern.

## 6.12 Coordinated Voters

These voters behave like a campaign or voting bloc.

Behavior:

1. Strongly favor a small set of target images.
2. Vote similarly across many sessions.
3. May appear in bursts.
4. May over-select a narrow cluster.

Expected detection:

1. High within-group agreement.
2. Timestamp clustering.
3. Repeated support for same image set.
4. Strong deviation from general population.
5. Possible anomaly flag.

---

## 7. Synthetic Bias Types

## 7.1 Cluster Bias

A voter segment over-selects one visual or description cluster.

Example:

1. Earthrise-style images.
2. Crew cabin images.
3. Moon close-ups.
4. Spacecraft exterior images.
5. Dramatic eclipse images.
6. Warm human-interest images.

Expected detection:

1. Cluster preference lift.
2. Cluster overrepresentation in top-N.
3. Redundancy penalty in calendar optimization.
4. Cluster-collapsed review reveals similar candidates.

## 7.2 Position Bias

Voters select based on display location.

Types:

1. First-image bias in batch.
2. Last-image bias in batch.
3. Left-side bias in pairwise.
4. Right-side bias in pairwise.
5. Top-rank default bias in category ranking.

Expected detection:

1. Logistic regression display-position effect.
2. Pairwise side imbalance.
3. Selection rate inflated by display position.
4. Warning in data quality report.

## 7.3 Exposure Bias

Some images are shown more often than others.

Types:

1. Popular images shown more often.
2. Certain clusters shown more often.
3. Newer images shown less often.
4. Category images shown unevenly.

Expected detection:

1. Difference between raw selected count and exposure-adjusted rate.
2. High uncertainty for low-exposure images.
3. Images with many selections but mediocre selection rate.
4. Images with high selection rate but low confidence.

## 7.4 Sentiment Bias

Some voters prefer descriptions with particular emotional tone.

Types:

1. Awe/wonder bias.
2. Human warmth bias.
3. Technical precision bias.
4. Isolation/solitude bias.
5. Dramatic language bias.

Expected detection:

1. Correlation between sentiment features and vote probability.
2. Text-cluster preference lift.
3. Month-fit bias.
4. Difference between visual and description cluster rankings.

## 7.5 Calendar-Slot Bias

Some voters implicitly select for month or cover suitability.

Types:

1. Cover-first bias.
2. January-opening bias.
3. December-closing bias.
4. Summer-brightness bias.
5. Human-interest month bias.

Expected detection:

1. Higher correlation with slot suitability scores.
2. Calendar optimizer identifies these images as strong slot candidates.
3. Top-N differs from slot-optimized slate.

## 7.6 Popularity Bias

Some voters prefer images already shown as popular.

This should be simulated only if the voting interface exposes popularity or if a social-influence scenario is being tested.

Expected detection:

1. Preference shifts after leaderboard exposure.
2. Later votes correlate more strongly with public rankings.
3. Reduced independent voter signal.

## 7.7 Coordinated Campaign Bias

A group intentionally promotes a small target set.

Expected detection:

1. High voter similarity within bloc.
2. Burst timing.
3. Target-image overperformance.
4. Disagreement with neutral voters.
5. Calendar optimizer avoids over-selecting campaign cluster.

## 7.8 Low-Information Bias

Voters make quick shallow selections.

Types:

1. Brightness bias.
2. Color bias.
3. Thumbnail-impact bias.
4. First-impression bias.

Expected detection:

1. Strong correlation with simple visual features.
2. Weak correlation with mission metadata.
3. Weak text-cluster signal.
4. High preference for cover-like images.

---

## 8. Synthetic Image Ground Truth

Each image should receive synthetic latent traits.

Recommended synthetic fields:

| Field                     | Description                   |
| ------------------------- | ----------------------------- |
| `latent_general_appeal`   | Broad underlying image appeal |
| `latent_visual_drama`     | Visual impact                 |
| `latent_story_value`      | Mission narrative value       |
| `latent_crew_value`       | Human/crew relevance          |
| `latent_technical_value`  | Technical interest            |
| `latent_cover_value`      | Cover suitability             |
| `latent_month_fit_json`   | Suitability by month          |
| `latent_redundancy_group` | Known redundancy group        |
| `latent_quality_score`    | Technical quality             |
| `latent_polarization`     | Expected disagreement         |
| `latent_cluster_id`       | Intended visual/text group    |

These traits can be derived from real features or manually assigned for testing.

---

## 9. Synthetic Voter Profile Model

Each synthetic voter should have a profile vector.

Example voter fields:

| Field                          | Description                                  |
| ------------------------------ | -------------------------------------------- |
| `synthetic_voter_profile_code` | neutral, visual_drama, crew, technical, etc. |
| `general_appeal_weight`        | Weight for broad appeal                      |
| `visual_drama_weight`          | Weight for visual drama                      |
| `story_value_weight`           | Weight for mission story                     |
| `crew_value_weight`            | Weight for crew/human images                 |
| `technical_value_weight`       | Weight for technical images                  |
| `cover_value_weight`           | Weight for cover-like images                 |
| `month_fit_weight`             | Weight for month suitability                 |
| `cluster_bias_json`            | Preferred or disliked clusters               |
| `sentiment_bias_json`          | Preferred description tones                  |
| `position_bias_strength`       | Display-position bias                        |
| `randomness_level`             | Noise level                                  |
| `fatigue_rate`                 | Increasing randomness over session           |
| `contrarian_strength`          | Anti-popularity behavior                     |
| `coordination_group_id`        | Campaign group if applicable                 |

---

## 10. Synthetic Vote Utility Function

For a voter `v` and image `i`, synthetic utility can be modeled as:

```text
utility(v, i) =
  voter.general_appeal_weight * image.latent_general_appeal
+ voter.visual_drama_weight * image.latent_visual_drama
+ voter.story_value_weight * image.latent_story_value
+ voter.crew_value_weight * image.latent_crew_value
+ voter.technical_value_weight * image.latent_technical_value
+ voter.cover_value_weight * image.latent_cover_value
+ voter.month_fit_weight * image.latent_month_fit
+ voter.cluster_bias_effect(i.cluster)
+ voter.sentiment_bias_effect(i.sentiment)
+ position_bias_effect
+ coordination_effect
+ random_noise
```

The generator should retain each component so test reports can compare detected effects against known ground truth.

---

## 11. Synthetic Batch Ballot Generation

## 11.1 Batch Ballot Process

For each synthetic batch ballot:

1. Select one synthetic voter.
2. Select 50 images for exposure.
3. Assign display positions.
4. Compute utility for each shown image.
5. Apply position bias if voter has it.
6. Apply fatigue/randomness if relevant.
7. Select top 5 images by noisy utility.
8. Save all 50 shown images.
9. Mark 5 selected images.
10. Mark 45 implicit rejections.
11. Save ground-truth generation details.

## 11.2 Batch Bias Tests

The batch generator should support:

1. Balanced exposure.
2. Uneven exposure.
3. Cluster-overexposure.
4. Position bias.
5. Voter fatigue.
6. Coordinated selection.
7. Random selection.
8. Contrarian selection.

Expected process detection:

1. Exposure-adjusted selection rate differs from raw counts.
2. Position bias appears in display-position model.
3. Cluster bias appears in cluster summaries.
4. Coordinated voting appears in voter-similarity analysis.
5. Fatigue appears in session-order consistency analysis.

---

## 12. Synthetic Pairwise Vote Generation

## 12.1 Pairwise Process

For each synthetic pairwise vote:

1. Select one synthetic voter.
2. Select two images.
3. Assign left/right position.
4. Compute utility for both images.
5. Apply side bias if voter has it.
6. Add random noise.
7. Select winner.
8. Save winner and loser.
9. Save left/right position if available.
10. Save ground-truth generation details.

## 12.2 Pairwise Bias Tests

The pairwise generator should support:

1. Left-side bias.
2. Right-side bias.
3. Strong cluster preference.
4. Random voting.
5. Coordinated target-image voting.
6. Fatigue over repeated comparisons.
7. High-noise voters.
8. Contrarian voters.

Expected process detection:

1. Left/right imbalance.
2. Elo inflation for target images.
3. Bradley-Terry-Luce score deviation.
4. High voter noise.
5. Low agreement with batch voting where expected.

---

## 13. Synthetic Category Ranking Generation

## 13.1 Category Ranking Process

For each category ranking:

1. Select one synthetic voter.
2. Select one category.
3. Select candidate images in that category.
4. Compute voter utility for each image.
5. Apply category-specific bias.
6. Rank top 3 images.
7. Assign Borda scores.
8. Save ranking details.
9. Save ground-truth generation details.

## 13.2 Category Bias Tests

The category generator should support:

1. Category preference bias.
2. Topic preference bias.
3. Description sentiment bias.
4. Default top-position bias.
5. Cluster over-selection.
6. Coordinated category targeting.

Expected process detection:

1. Category-specific preference lift.
2. Text-cluster concentration.
3. Borda score distortion.
4. Differences between category ranking and batch voting.

---

## 14. Synthetic Calendar Preference Test

The synthetic data should include a known ideal calendar slate.

This should include:

1. 1 known best cover image.
2. 12 known monthly images.
3. Alternate strong candidates.
4. Redundant high-scoring distractors.
5. Popular but redundant images.
6. Lower-ranked but month-appropriate images.
7. High-appeal images that should not all be selected together.

## 14.1 Calendar Test Design

Create three synthetic candidate groups:

| Group             | Description                                               |
| ----------------- | --------------------------------------------------------- |
| True calendar set | Best cover plus 12 monthly images by ground truth         |
| Naive top-N set   | Highest individual appeal images, intentionally redundant |
| Biased top-N set  | Images favored by biased voter blocs                      |

The system should show that:

1. Naive top-N has high appeal but poor diversity.
2. Biased top-N has suspicious support and poor representativeness.
3. Optimized calendar set has better total utility.
4. Cover image is selected for cover-specific reasons.
5. Monthly images are selected for month-specific fit and collection balance.

---

## 15. Synthetic Ground Truth Tables

## 15.1 `synthetic_voter_profile`

**Grain:** one synthetic voter profile type.

| Column                    | Description                    |
| ------------------------- | ------------------------------ |
| `synthetic_profile_code`  | Profile name                   |
| `profile_description`     | Human-readable behavior        |
| `general_appeal_weight`   | Broad appeal weight            |
| `visual_drama_weight`     | Visual drama weight            |
| `story_value_weight`      | Mission story weight           |
| `crew_value_weight`       | Crew preference weight         |
| `technical_value_weight`  | Technical preference weight    |
| `cover_value_weight`      | Cover preference weight        |
| `month_fit_weight`        | Month fit preference weight    |
| `position_bias_strength`  | Display-position bias          |
| `randomness_level`        | Randomness/noise               |
| `fatigue_rate`            | Fatigue effect                 |
| `contrarian_strength`     | Anti-popularity behavior       |
| `coordination_group_flag` | Whether profile is coordinated |
| `expected_detection_json` | Expected findings              |

## 15.2 `synthetic_voter_assignment`

**Grain:** one synthetic voter.

| Column                   | Description               |
| ------------------------ | ------------------------- |
| `synthetic_run_id`       | Generation run            |
| `voter_sk`               | Synthetic voter surrogate |
| `synthetic_profile_code` | Assigned profile          |
| `coordination_group_id`  | Campaign group if any     |
| `random_seed`            | Reproducibility           |
| `ground_truth_json`      | Restricted known truth    |

## 15.3 `synthetic_image_truth`

**Grain:** one image within one synthetic run.

| Column                       | Description                                   |
| ---------------------------- | --------------------------------------------- |
| `synthetic_run_id`           | Generation run                                |
| `image_sk`                   | Image key                                     |
| `latent_general_appeal`      | Broad appeal                                  |
| `latent_visual_drama`        | Visual impact                                 |
| `latent_story_value`         | Mission story value                           |
| `latent_crew_value`          | Crew/human value                              |
| `latent_technical_value`     | Technical interest                            |
| `latent_cover_value`         | Cover suitability                             |
| `latent_quality_score`       | Technical suitability                         |
| `latent_polarization`        | Expected disagreement                         |
| `latent_month_fit_json`      | Month fit scores                              |
| `latent_redundancy_group`    | Known redundant group                         |
| `expected_rank_band`         | high, medium, low                             |
| `ground_truth_calendar_role` | cover, month, alternate, distractor, suppress |

## 15.4 `synthetic_vote_truth`

**Grain:** one generated voting event.

| Column                    | Description              |
| ------------------------- | ------------------------ |
| `synthetic_run_id`        | Generation run           |
| `vote_session_sk`         | Vote session             |
| `vote_mode_sk`            | Vote mode                |
| `voter_sk`                | Voter                    |
| `bias_profile_code`       | Active bias profile      |
| `position_bias_applied`   | True/false               |
| `cluster_bias_applied`    | True/false               |
| `coordination_applied`    | True/false               |
| `fatigue_applied`         | True/false               |
| `random_noise_level`      | Noise value              |
| `expected_detection_json` | Expected process finding |

---

## 16. Synthetic Run Control

## 16.1 `ctl_synthetic_generation_run`

| Column                   | Description                           |
| ------------------------ | ------------------------------------- |
| `synthetic_run_id`       | Unique generation run                 |
| `base_image_load_run_id` | Image data version                    |
| `profile_config_hash`    | Voter profile config hash             |
| `random_seed`            | Reproducibility                       |
| `voter_count`            | Number of synthetic voters            |
| `batch_ballot_count`     | Number of generated batch ballots     |
| `pairwise_vote_count`    | Number of generated pairwise votes    |
| `category_ranking_count` | Number of generated category rankings |
| `bias_scenario_code`     | Scenario name                         |
| `created_at`             | Generation timestamp                  |
| `notes`                  | Run notes                             |

## 16.2 Required Reproducibility Rules

1. Every generation run must have a random seed.
2. Every generation run must have a config hash.
3. Every synthetic record must reference `synthetic_run_id`.
4. Synthetic data must be clearly separable from real data.
5. Ground truth must be stored separately from model input.
6. Model evaluation may use ground truth only after scoring is complete.

---

## 17. Bias Scenarios

## 17.1 Scenario A: Mostly Neutral Population

Purpose:

Test the system under ordinary conditions.

Population:

| Voter Type    | Share |
| ------------- | ----: |
| Neutral       |   70% |
| Visual drama  |   10% |
| Mission story |   10% |
| Crew-focused  |    5% |
| Random        |    5% |

Expected outcome:

1. Broad appeal scores are stable.
2. Inter-rater reliability is moderate.
3. Optimized calendar differs somewhat from top-N due to diversity.
4. Bias warnings are minimal.

## 17.2 Scenario B: Visual Cluster Overload

Purpose:

Test whether the system detects over-selection of one visually dominant cluster.

Population:

| Voter Type    | Share |
| ------------- | ----: |
| Visual drama  |   45% |
| Neutral       |   35% |
| Mission story |   10% |
| Random        |   10% |

Expected outcome:

1. Dramatic Earth/Moon cluster dominates raw rankings.
2. Cluster report identifies overconcentration.
3. Calendar optimizer suppresses redundant images.
4. Top-N baseline performs worse than optimized slate.

## 17.3 Scenario C: Position Bias

Purpose:

Test whether the system identifies display-position bias.

Population:

| Voter Type      | Share |
| --------------- | ----: |
| Neutral         |   50% |
| Position-biased |   30% |
| Random          |   20% |

Expected outcome:

1. First-position images are selected too often.
2. Left-side pairwise images win too often.
3. Position-bias warning is generated.
4. Corrected preference scores differ from raw scores.

## 17.4 Scenario D: Coordinated Campaign

Purpose:

Test whether the system detects a voting bloc.

Population:

| Voter Type   | Share |
| ------------ | ----: |
| Neutral      |   60% |
| Coordinated  |   20% |
| Visual drama |   10% |
| Random       |   10% |

Expected outcome:

1. Target images receive abnormal support.
2. Coordinated voters show high similarity.
3. Target cluster has suspicious lift.
4. Calendar optimizer does not blindly select all targets.

## 17.5 Scenario E: Description Sentiment Bias

Purpose:

Test whether description sentiment and topic affect voting.

Population:

| Voter Type    | Share |
| ------------- | ----: |
| Mission story |   35% |
| Crew-focused  |   20% |
| Technical     |   15% |
| Neutral       |   20% |
| Random        |   10% |

Expected outcome:

1. Description clusters predict votes.
2. Sentiment/tone features show measurable effect.
3. Some visually weaker images rank well due to description strength.
4. Calendar optimizer balances story value and visual quality.

## 17.6 Scenario F: Cover Bias

Purpose:

Test whether cover-like images dominate when voters choose as if selecting a poster.

Population:

| Voter Type         | Share |
| ------------------ | ----: |
| Cover-image voters |   50% |
| Neutral            |   30% |
| Month-fit voters   |   10% |
| Random             |   10% |

Expected outcome:

1. High cover-suitability images dominate raw rankings.
2. Cover candidate is clear.
3. Monthly slate needs additional diversity.
4. Top-N would over-select cover-like images.

## 17.7 Scenario G: Month-Fit Population

Purpose:

Test whether voters implicitly support a better calendar collection.

Population:

| Voter Type       | Share |
| ---------------- | ----: |
| Month-fit voters |   45% |
| Mission story    |   20% |
| Neutral          |   25% |
| Random           |   10% |

Expected outcome:

1. Selected images are more diverse.
2. Slot suitability is higher.
3. Calendar optimizer aligns well with voter preferences.
4. Top-N baseline is less poor than in visual-overload scenarios.

---

## 18. Expected Detection Metrics

## 18.1 Cluster Bias Detection

Metrics:

1. Selection lift by cluster.
2. Pairwise win lift by cluster.
3. Category score lift by cluster.
4. Cluster representation in top-N.
5. Cluster representation in optimized slate.
6. Cluster overconcentration penalty.

Expected output:

| Finding                        | Example                                               |
| ------------------------------ | ----------------------------------------------------- |
| Overrepresented visual cluster | Earth/Moon eclipse images selected 2.7x expected rate |
| Redundant top images           | 8 of top 13 from same visual cluster                  |
| Optimization correction        | Calendar slate limits this cluster to 2 images        |

## 18.2 Position Bias Detection

Metrics:

1. Selection rate by batch display position.
2. Pairwise win rate by left/right side.
3. Rank defaulting in category workflows.
4. Regression coefficient for display position.

Expected output:

| Finding             | Example                                        |
| ------------------- | ---------------------------------------------- |
| First-position bias | Images in positions 1-5 selected 1.4x expected |
| Left-side bias      | Left image wins 58% of comparisons             |
| Corrective flag     | Position-bias adjustment recommended           |

## 18.3 Coordinated Voting Detection

Metrics:

1. Voter similarity.
2. Target image lift.
3. Burst timing.
4. Low diversity within voter bloc.
5. Shared unusual selections.

Expected output:

| Finding           | Example                                               |
| ----------------- | ----------------------------------------------------- |
| Coordinated group | 87 voters show unusually similar target selections    |
| Target lift       | Target images selected 4.1x expected by bloc          |
| Slate protection  | Calendar optimizer avoids over-selecting target group |

## 18.4 Sentiment Bias Detection

Metrics:

1. Vote probability by sentiment score.
2. Vote probability by emotion label.
3. Text-cluster preference lift.
4. Difference between visual and text cluster rankings.

Expected output:

| Finding              | Example                                         |
| -------------------- | ----------------------------------------------- |
| Awe bias             | High-awe descriptions selected 1.8x expected    |
| Human warmth bias    | Crew descriptions overperform among one segment |
| Technical topic bias | Technical descriptions polarize voters          |

## 18.5 Calendar Fit Detection

Metrics:

1. Cover score correlation with votes.
2. Month score correlation with votes.
3. Optimized slate month-fit average.
4. Top-N month-fit average.
5. Cover-vs-month role separation.

Expected output:

| Finding               | Example                                              |
| --------------------- | ---------------------------------------------------- |
| Cover dominance       | Top-ranked images are cover-like but redundant       |
| Month fit improvement | Optimized slate improves average month score by 22%  |
| Cover separation      | Best cover image is not forced into monthly sequence |

---

## 19. Evaluation Framework

Each synthetic run should produce a bias-detection evaluation.

## 19.1 Required Evaluation Questions

1. Did the system identify the intended biased voter segments?
2. Did the system identify intentionally overrepresented clusters?
3. Did the system identify position bias?
4. Did the system identify coordinated voting behavior?
5. Did the system distinguish cover suitability from month suitability?
6. Did the optimized calendar beat the naive top-N baseline?
7. Did the system avoid selecting redundant images?
8. Did the system preserve strong images from underrepresented clusters?
9. Did the system correctly flag low-confidence images?
10. Did the system document its reasoning?

## 19.2 Evaluation Metrics

| Metric                           | Meaning                                                 |
| -------------------------------- | ------------------------------------------------------- |
| Bias detection precision         | How many flagged biases were real                       |
| Bias detection recall            | How many planted biases were found                      |
| Cluster overrepresentation error | Difference between expected and observed cluster share  |
| Position-bias coefficient error  | Difference between planted and estimated effect         |
| Coordinated-group detection rate | Share of planted campaign voters detected               |
| Calendar slate recovery          | Share of ground-truth calendar images recovered         |
| Cover recovery                   | Whether ground-truth cover was selected or top-ranked   |
| Month assignment accuracy        | Share of images assigned to intended month              |
| Redundancy reduction             | Difference between top-N and optimized slate redundancy |
| Utility improvement              | Optimized slate score over naive top-N                  |

---

## 20. Synthetic Data Volume

Initial recommended synthetic dataset:

| Item                        |   Count |
| --------------------------- | ------: |
| Synthetic voters            |   1,000 |
| Batch ballots               |  10,000 |
| Batch exposures             | 500,000 |
| Batch selections            |  50,000 |
| Pairwise votes              |  50,000 |
| Category rankings           |   5,000 |
| Synthetic scenarios         |       7 |
| Synthetic runs per scenario |       3 |

Smaller development dataset:

| Item              | Count |
| ----------------- | ----: |
| Synthetic voters  |   100 |
| Batch ballots     |   500 |
| Pairwise votes    | 2,000 |
| Category rankings |   250 |

---

## 21. Synthetic Data Acceptance Criteria

| ID         | Criterion                                                    |
| ---------- | ------------------------------------------------------------ |
| AC-SYN-001 | Synthetic voters are generated with known profile labels     |
| AC-SYN-002 | Synthetic images have ground-truth latent scores             |
| AC-SYN-003 | Batch ballots include shown and selected images              |
| AC-SYN-004 | Pairwise votes include winner and loser                      |
| AC-SYN-005 | Category rankings include rank position                      |
| AC-SYN-006 | Position bias can be turned on and off                       |
| AC-SYN-007 | Cluster bias can be turned on and off                        |
| AC-SYN-008 | Coordinated voting can be turned on and off                  |
| AC-SYN-009 | Sentiment bias can be turned on and off                      |
| AC-SYN-010 | Cover bias can be turned on and off                          |
| AC-SYN-011 | Month-fit bias can be turned on and off                      |
| AC-SYN-012 | Generated data is reproducible by random seed                |
| AC-SYN-013 | Synthetic records are clearly marked as synthetic            |
| AC-SYN-014 | Ground truth is not used during model fitting                |
| AC-SYN-015 | Bias detection report compares findings to ground truth      |
| AC-SYN-016 | Calendar optimizer is evaluated against naive top-N baseline |
| AC-SYN-017 | Cover plus 12 monthly images are evaluated separately        |

---

## 22. Synthetic Data Risks

| Risk                                              | Severity | Mitigation                                                |
| ------------------------------------------------- | -------- | --------------------------------------------------------- |
| Synthetic data too clean                          | Medium   | Add realistic noise and missingness                       |
| Synthetic bias too obvious                        | Medium   | Use subtle and mixed bias strengths                       |
| Synthetic profiles unrealistic                    | Medium   | Mix multiple profiles per voter                           |
| Ground truth leaks into model                     | High     | Keep ground truth in separate restricted tables           |
| Position bias unavailable in real data            | Medium   | Make position-bias tests conditional                      |
| Overfitting to synthetic scenarios                | Medium   | Use multiple scenarios and random seeds                   |
| Calendar ground truth too subjective              | Medium   | Define several valid reference slates                     |
| Bias detection too punitive                       | Medium   | Distinguish preference segments from malicious behavior   |
| Coordinated voting confused with niche preference | High     | Use timing, similarity, and target concentration together |

---

## 23. Implementation Phases

## 23.1 Phase S1: Synthetic Profile Design

Deliverables:

1. Voter profile definitions.
2. Bias scenario definitions.
3. Synthetic image latent trait schema.
4. Ground-truth table design.

Exit criteria:

1. Profiles reviewed.
2. Biases mapped to expected detection methods.
3. Ground-truth fields finalized.

## 23.2 Phase S2: Synthetic Vote Generator

Deliverables:

1. Batch ballot generator.
2. Pairwise vote generator.
3. Category ranking generator.
4. Random seed control.
5. Synthetic run-control table.

Exit criteria:

1. Synthetic records load into normal fact tables.
2. Records are marked synthetic.
3. Re-running same seed reproduces same output.

## 23.3 Phase S3: Bias Detection Validation

Deliverables:

1. Bias detection report.
2. Cluster bias evaluation.
3. Position bias evaluation.
4. Coordinated voting evaluation.
5. Sentiment bias evaluation.
6. Cover/month bias evaluation.

Exit criteria:

1. Planted biases are detected.
2. False positives are documented.
3. Missed biases are documented.
4. Detection thresholds are calibrated.

## 23.4 Phase S4: Calendar Optimization Validation

Deliverables:

1. Naive top-N calendar.
2. Biased top-N calendar.
3. Optimized calendar.
4. Ground-truth calendar comparison.
5. Cover-specific evaluation.
6. Monthly slot evaluation.

Exit criteria:

1. Optimized slate improves over naive top-N.
2. Cover image is selected or ranked highly.
3. Monthly images are more diverse than naive top-N.
4. Selection reasons match known ground truth.

---

## 24. Required Reports

## 24.1 Synthetic Generation Report

Must include:

1. Synthetic run ID.
2. Random seed.
3. Number of voters.
4. Number of votes.
5. Bias scenario.
6. Voter profile mix.
7. Image latent trait summary.
8. Generated vote summary.
9. Expected detection outcomes.

## 24.2 Bias Detection Report

Must include:

1. Biases planted.
2. Biases detected.
3. Biases missed.
4. False positives.
5. Cluster-bias findings.
6. Position-bias findings.
7. Sentiment-bias findings.
8. Coordinated-voting findings.
9. Cover/month bias findings.
10. Detection precision and recall.

## 24.3 Synthetic Calendar Validation Report

Must include:

1. Ground-truth cover image.
2. Ground-truth monthly images.
3. Naive top-13 by score.
4. Optimized cover plus 12 months.
5. Recovery rate.
6. Redundancy comparison.
7. Month-fit comparison.
8. Cover-fit comparison.
9. Explanation quality review.

---

## 25. Lessons Learned Additions

Add these lessons to the main project lesson registry:

| Lesson | Topic                                                     |
| ------ | --------------------------------------------------------- |
| 016    | Synthetic voter data for pipeline validation              |
| 017    | Designing intentional bias for model testing              |
| 018    | Separating preference segments from bad data              |
| 019    | Detecting position bias                                   |
| 020    | Detecting cluster overrepresentation                      |
| 021    | Detecting coordinated voting                              |
| 022    | Evaluating calendar optimization with ground truth        |
| 023    | Testing cover selection separately from monthly selection |
| 024    | Why synthetic data needs known truth                      |
| 025    | Avoiding ground-truth leakage                             |

---

## 26. Summary

This synthetic voter-data design allows the Artemis II calendar project to test its own assumptions before relying on real voter records.

The synthetic generator should create representative voters, biased voters, random voters, fatigued voters, and coordinated voter blocs. It should generate batch ballots, pairwise votes, and category rankings using known latent image traits and known voter bias profiles.

The analysis system should then attempt to detect the planted biases without access to the ground truth during modeling. Afterward, the results should be compared against the known synthetic truth.

The most important validation question is:

**Can the system select a strong 13-image calendar — one cover plus 12 monthly images — while detecting and correcting for biased voting patterns that would distort a simple top-N ranking?**
