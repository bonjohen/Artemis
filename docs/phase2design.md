Artemis Detailed Design Document: Biased Voting Blocks, Vision Tagging, Clustering, and Static Statistical Reporting

1. Purpose

The Artemis project should be extended to support controlled statistical analysis of biased voting behavior over image-selection results.

The goal is to let the local/admin pipeline generate synthetic or semi-synthetic voter groups with predefined image-selection biases, analyze how those groups affect results, and publish aggregate statistical summaries on the static Artemis website.

A second goal is to improve image understanding by adding a local vision-analysis pipeline that identifies solar-system and Artemis-relevant image attributes such as Earth, Moon, Sun, Earth+Moon, Moon+Sun, spacecraft, astronaut, launch, surface, interior, and deep space. These labels should support clustering, voting-bias analysis, and static-site visualization.

The public static website should remain a read-only reporting surface. It should display analysis, summaries, charts, and visualizations, but should not expose controls for generating voters, creating voting blocks, changing model settings, or running pipelines.


---

2. Current Project Context

Artemis already appears to contain the core pieces needed for this extension:

Image-selection workflows.

Voting-related data structures.

Synthetic voter concepts.

Statistical scoring.

Bias-detection concepts.

Pipeline-oriented data integration.

Static website generation.

A stats page intended to display public analysis.

Local/admin tooling through CLI-style workflows.


The existing project direction is already compatible with the desired architecture: local generation and processing first, static publication second.

The new work should extend this structure rather than introduce a separate system.


---

3. High-Level Target Architecture

The extended system should have five major layers:

1. Image Vision Analysis Layer
Uses local vision models to generate image captions, attribute labels, confidence scores, embeddings, and cluster assignments.


2. Voting Block Generation Layer
Uses local/admin configuration files to define biased voter groups and generate synthetic voting behavior.


3. Statistical Analysis Layer
Calculates vote results, block-level bias effects, image-attribute lift, cluster lift, score impact, and confidence measures.


4. Pipeline/Static Build Layer
Converts generated analysis into static JSON artifacts for the website.


5. Public Static Website Layer
Displays read-only results, charts, summaries, cluster views, and bias-detection explanations.




---

4. Core Design Principle

The project should maintain a strict separation between:

Local/admin capabilities

These are allowed locally:

Running local vision models.

Generating image labels.

Generating embeddings.

Creating clusters.

Defining voting blocks.

Generating synthetic voters.

Generating synthetic votes.

Running statistical analysis.

Building static JSON.

Building the public static site.


Public website capabilities

These are allowed publicly:

Viewing aggregate statistics.

Viewing image clusters.

Viewing cluster labels.

Viewing voting-block summaries.

Viewing bias-detection results.

Viewing score distributions.

Viewing image-selection impact.

Viewing static visualizations.


Public website restrictions

These should not be exposed publicly:

Voting-block creation.

Synthetic vote generation.

Admin configuration editing.

Model prompts.

Local model settings.

Raw voter-level records.

Raw synthetic vote traces.

Pipeline execution controls.

POST/write endpoints.

Re-run buttons.

Local file paths.

Random seeds.

Admin-only metadata.



---

5. Existing Voting and Statistics Capabilities

The project already appears to have several relevant voting concepts:

Random or batch-style voting.

Pairwise/head-to-head voting.

Ranked/category voting.

Synthetic voter support.

Synthetic run identifiers.

Voter profiles.

Statistical scoring.

Bias detection.

Static stats reporting.


The current synthetic voter system appears to include broad behavioral profiles such as neutral, visual-drama, position-biased, and random. These are useful, but they are not yet specific enough for the desired work.

The desired work requires configurable voter blocks such as:

25 voters who prefer images containing both Earth and Moon.

20 voters who prefer Earth-only images.

30 voters who prefer images containing both Moon and Sun.

Other local/admin-defined groups with custom image-selection preferences.


This requires explicit image attributes and explicit preference rules.


---

6. Image Vision Analysis Design

6.1 Purpose

The vision-analysis layer should identify Artemis-relevant image attributes so that both clustering and voting-bias generation can operate on structured image features.

The system should not rely only on filenames, captions, or manually entered metadata. Those may be useful, but the ideal system should use local vision models to produce richer labels.

6.2 Recommended Local Model Stack

The recommended first implementation is:

Qwen2.5-VL 7B or 3B for image understanding, captions, and structured labels.

SigLIP or OpenCLIP for image embeddings.

HDBSCAN or K-Means for clustering.

Optional Florence-2 for secondary captioning or object evidence.

Optional Grounding DINO / OWLv2 / YOLO-World for object-level detection.

Optional SAM 2 for segmentation, only if masks are needed.


6.3 Recommended First Version

Use:

Qwen2.5-VL 7B for structured labels
SigLIP for embeddings
HDBSCAN for natural cluster discovery
K-Means for fixed-number cluster experiments
Manual review queue for low-confidence labels

This gives the project:

Human-readable labels.

Machine-usable attributes.

Embeddings for clustering.

Cluster summaries.

Confidence scores.

A practical path toward static reporting.


6.4 Image Attribute Vocabulary

The project should define a controlled vocabulary for image attributes.

Initial attributes:

earth
moon
sun
earth_and_moon
earth_only
moon_and_sun
sun_only
deep_space
spacecraft
astronaut
crew
rocket
launch
surface
lunar_surface
earth_surface
interior
vehicle
habitat
mission_control
diagram
map
text_overlay
artistic_rendering
photograph
low_confidence

Derived attributes should be computed from base labels.

Examples:

earth_and_moon = earth AND moon
earth_only = earth AND NOT moon AND NOT sun
moon_and_sun = moon AND sun
sun_only = sun AND NOT earth AND NOT moon

6.5 Vision Output Per Image

Each image should receive a structured record:

{
  "image_id": "artemis_002341",
  "caption": "Earth and Moon visible against dark space.",
  "attributes": {
    "earth": 0.97,
    "moon": 0.91,
    "sun": 0.08,
    "spacecraft": 0.12,
    "deep_space": 0.94
  },
  "derived_labels": [
    "earth",
    "moon",
    "earth_and_moon",
    "deep_space"
  ],
  "embedding_model": "siglip",
  "vision_model": "qwen2.5-vl-7b",
  "cluster_id": "cluster_014",
  "cluster_label": "Earth and Moon in deep space",
  "review_flag": false
}

6.6 Confidence Handling

Each attribute should have a confidence score.

Recommended thresholds:

>= 0.80 = accepted label
0.50 to 0.79 = tentative label
< 0.50 = rejected label

Images should be flagged for review when:

Core attributes conflict.

Confidence is low.

The model identifies rare combinations.

The image has text, diagrams, or unusual rendering.

The image is a likely calendar finalist.

The image strongly affects voting-block results.



---

7. Clustering Design

7.1 Purpose

Clustering should group visually and semantically similar images.

Clusters should support:

Browsing the image library.

Understanding overrepresented visual themes.

Selecting representative images.

Detecting voting-block bias.

Explaining voting outcomes.

Summarizing calendar image diversity.


7.2 Inputs

Clustering should use:

Image embeddings.

Vision-generated labels.

Existing image metadata.

Captions/descriptions.

Optional manual labels.


7.3 Cluster Output

Each image should receive:

cluster_id
cluster_distance
cluster_confidence
nearest_neighbor_ids
representative_rank_within_cluster

Each cluster should receive:

cluster_id
cluster_label
cluster_summary
image_count
dominant_attributes
representative_images
outlier_images
average_score
average_vote_count
average_selection_rate
voting_block_lift_summary

7.4 Cluster Labeling

Cluster labels should be generated from dominant attributes and representative captions.

Example labels:

Earth and Moon in deep space
Moon surface and astronaut activity
Launch vehicle and smoke plume
Spacecraft interior and crew operations
Solar imagery and high-contrast light
Earth-only orbital views

7.5 Cluster Review

The local/admin workflow should provide a review file for clusters:

outputs/review/cluster_review.json
outputs/review/cluster_review.md

This should include:

Cluster ID.

Proposed label.

Representative images.

Dominant attributes.

Outliers.

Confidence.

Suggested manual corrections.



---

8. Voting Block Design

8.1 Purpose

Voting blocks allow Artemis to model intentionally biased groups of voters.

A voting block is a named group of synthetic voters with predefined image-selection preferences.

Example:

Earth+Moon Enthusiasts
25 voters
Prefer images containing both Earth and Moon
Moderate randomness
High preference strength

8.2 Voting Block Config File

Voting blocks should be defined locally using YAML or JSON.

Recommended path:

config/voting_blocks/

Example:

scenario_id: earth_moon_bias_test
scenario_name: Earth / Moon / Sun Bias Test
description: Synthetic test scenario with three biased voting blocks.
seed: 42

blocks:
  - block_id: earth_moon_block
    label: Earth and Moon Preference Block
    voter_count: 25
    votes_per_voter: 40
    preference_rules:
      all_of:
        - earth
        - moon
      any_of: []
      none_of: []
    preference_weight: 2.5
    randomness_weight: 0.35

  - block_id: earth_only_block
    label: Earth-Only Preference Block
    voter_count: 20
    votes_per_voter: 40
    preference_rules:
      all_of:
        - earth
      any_of: []
      none_of:
        - moon
        - sun
    preference_weight: 2.2
    randomness_weight: 0.40

  - block_id: moon_sun_block
    label: Moon and Sun Preference Block
    voter_count: 30
    votes_per_voter: 40
    preference_rules:
      all_of:
        - moon
        - sun
      any_of: []
      none_of: []
    preference_weight: 2.6
    randomness_weight: 0.30

  - block_id: neutral_control
    label: Neutral Control Voters
    voter_count: 50
    votes_per_voter: 40
    preference_rules:
      all_of: []
      any_of: []
      none_of: []
    preference_weight: 0.0
    randomness_weight: 1.0

8.3 Preference Rule Types

Supported rule types:

all_of
any_of
none_of
weighted_attributes
cluster_preference
image_whitelist
image_blacklist
score_band_preference
novelty_preference

Initial implementation should support:

all_of
any_of
none_of
weighted_attributes

Later versions can add:

cluster_preference
coordinated_targeting
time-window behavior
position bias
ballot stuffing simulation
adversarial voting

8.4 Voting Utility Function

Each synthetic voter should calculate image utility using a weighted score.

Recommended first version:

utility =
  baseline_image_quality
  + attribute_match_score
  + cluster_preference_score
  + latent_appeal_score
  + randomness
  - penalty_for_none_of_match

For a specific voting block:

attribute_match_score =
  preference_weight * rule_match_strength

Example:

Earth+Moon voter:
earth image only = partial match
moon image only = partial match
earth + moon image = strong match
moon + sun image = weak or neutral match

8.5 Voter-Level Assignment

Each synthetic voter should be assigned to:

synthetic_run_id
scenario_id
block_id
synthetic_profile_code
random_seed

The public site should not expose individual voters.


---

9. Local/Admin CLI Workflow

9.1 Desired Commands

The CLI should support a vision-analysis pipeline and a voting-block pipeline.

Recommended commands:

artemis vision tag-images
artemis vision embed-images
artemis vision cluster-images
artemis vision summarize-clusters

artemis votes generate-blocks
artemis stats compute
artemis stats compute-block-analysis
artemis static build

Or as a combined pipeline:

artemis pipeline run --profile local-biased-vote-analysis

9.2 Voting Block Generation Command

Recommended command:

artemis votes generate-blocks \
  --config config/voting_blocks/earth_moon_bias_test.yaml \
  --run-name earth_moon_bias_test \
  --seed 42 \
  --replace-run

Useful options:

--config
--run-name
--seed
--replace-run
--append-run
--dry-run
--voter-count-multiplier
--votes-per-voter
--output-summary
--write-review-files

9.3 Dry Run Behavior

Dry run should validate:

Config syntax.

Required fields.

Attribute names.

Block IDs.

Rule structure.

Image match counts per rule.

Expected number of voters.

Expected number of votes.

Whether each block has enough matching images.


Dry-run output should include:

Scenario: Earth / Moon / Sun Bias Test

Block: Earth and Moon Preference Block
Voters: 25
Votes per voter: 40
Matching images: 318
Warning: none

Block: Earth-Only Preference Block
Voters: 20
Votes per voter: 40
Matching images: 612
Warning: none

Block: Moon and Sun Preference Block
Voters: 30
Votes per voter: 40
Matching images: 47
Warning: low image count; consider lowering preference strength or adding fallback behavior


---

10. Data Model Changes

10.1 Image Attribute Tables

Add:

dim_image_attribute
feature_image_attribute

dim_image_attribute

attribute_code
attribute_label
attribute_description
attribute_type
is_derived
created_at
updated_at

Example rows:

earth
moon
sun
earth_and_moon
earth_only
moon_and_sun
spacecraft
astronaut
deep_space

feature_image_attribute

image_id
attribute_code
confidence_score
label_source
model_name
model_version
run_id
is_accepted
is_manual_override
created_at

10.2 Image Embedding Table

Add:

feature_image_embedding

Fields:

image_id
embedding_model
embedding_version
embedding_vector
embedding_dimension
run_id
created_at

Depending on storage approach, embeddings can be stored in:

Database vector column.

Serialized binary.

Parquet.

NumPy files.

External feature store file with DB pointer.


10.3 Cluster Tables

Add:

dim_image_cluster_run
dim_image_cluster
bridge_image_cluster_assignment

dim_image_cluster_run

cluster_run_id
embedding_model
cluster_algorithm
cluster_parameters_json
created_at
notes

dim_image_cluster

cluster_run_id
cluster_id
cluster_label
cluster_summary
image_count
dominant_attributes_json
representative_image_ids_json
created_at

bridge_image_cluster_assignment

cluster_run_id
cluster_id
image_id
cluster_distance
cluster_confidence
representative_rank
is_outlier

10.4 Voting Block Tables

Add:

dim_voting_scenario
dim_voting_block
voting_block_rule
synthetic_voter_block_assignment

dim_voting_scenario

scenario_id
scenario_name
description
seed
config_hash
created_at
created_by

dim_voting_block

block_id
scenario_id
block_label
voter_count
votes_per_voter
preference_weight
randomness_weight
description
created_at

voting_block_rule

block_id
rule_type
attribute_code
rule_weight
created_at

Example rule types:

all_of
any_of
none_of
weighted_attribute

synthetic_voter_block_assignment

voter_id
synthetic_run_id
scenario_id
block_id
synthetic_profile_code
created_at

10.5 Mart Tables

Add:

mart_voting_block_summary
mart_voting_block_attribute_lift
mart_voting_block_cluster_lift
mart_voting_block_image_lift
mart_voting_block_similarity
mart_voting_block_score_impact
mart_voting_block_calendar_impact


---

11. Statistical Analysis Design

11.1 Existing Statistics to Preserve

Continue calculating:

selection rate
vote count
Wilson lower bound
Beta-Binomial posterior mean
Beta-Binomial confidence interval
Elo score
Borda score
composite score
uncertainty
polarization
broad appeal
inter-rater reliability
score distribution
cluster bias
position bias

11.2 New Voting Block Statistics

For each voting block:

voter count
vote count
selected image count
selection rate
expected selection rate
lift over baseline
confidence interval
top selected images
top rejected images
dominant selected attributes
dominant selected clusters

11.3 Attribute Lift

For each block and attribute:

block_id
attribute_code
block_selection_rate
global_selection_rate
lift
odds_ratio
selected_count
exposed_count
confidence_interval_low
confidence_interval_high

Example:

Earth+Moon block:
earth_and_moon lift = 3.8x
earth_only lift = 0.7x
moon_and_sun lift = 1.1x

11.4 Cluster Lift

For each block and cluster:

block_id
cluster_id
cluster_label
block_selection_rate
global_selection_rate
lift
chi_square_contribution
selected_count
expected_count

11.5 Block Similarity

For each pair of blocks:

block_a
block_b
jaccard_top_n
cosine_similarity
score_correlation
top_image_overlap_count
top_cluster_overlap_count

This helps identify whether two different stated preferences behave similarly in practice.

11.6 Score Impact

For each block:

image_id
score_with_block
score_without_block
score_delta
rank_with_block
rank_without_block
rank_delta
block_influence_score

This identifies which images were promoted or suppressed by each biased voting block.

11.7 Calendar Impact

For each voting scenario:

selected_calendar_images_with_blocks
selected_calendar_images_without_block
cover_image_with_blocks
cover_image_without_block
changed_month_count
changed_cover_flag
diversity_score_delta
attribute_distribution_delta
cluster_distribution_delta

This shows whether the biased blocks changed the final calendar candidate set.

11.8 Bias Detection Result

Each intended voting block should produce a detection summary:

block_id
intended_bias
detected_bias
detection_strength
primary_evidence
secondary_evidence
confidence
status

Example statuses:

detected
partially_detected
not_detected
inconclusive


---

12. Static Website Design

12.1 Stats Page Additions

The /stats page should display:

Voting Bias Analysis
Vision Label Summary
Cluster Summary
Attribute Lift
Cluster Lift
Block Similarity
Score Impact
Calendar Impact
Synthetic Scenario Summary

12.2 Voting Scenario Summary

Display:

Scenario name
Generation date
Synthetic run ID
Number of voters
Number of votes
Number of voting blocks
Number of image attributes
Number of clusters
Overall detection result

12.3 Voting Block Summary

Display one card per block:

Block name
Preference rule summary
Voter count
Vote count
Top matching attributes
Strongest attribute lift
Strongest cluster lift
Top promoted image
Bias detection status

Example:

Earth and Moon Preference Block
25 voters
1,000 votes
Rule: earth AND moon
Strongest lift: earth_and_moon, 3.8x
Top cluster: Earth and Moon in deep space
Detection: detected

12.4 Cluster View

Display:

Cluster label
Representative images
Image count
Dominant attributes
Average score
Top voting block
Block lift summary

12.5 Image Attribute Summary

Display:

Attribute
Image count
Average score
Selection rate
Top voting block
Lift

12.6 Score Impact View

Display:

Images most promoted by biased voting blocks
Images most suppressed by biased voting blocks
Images whose calendar rank changed
Images whose cover candidacy changed

12.7 Visualization Types

Recommended visualizations:

Score distribution chart
Attribute count bar chart
Attribute lift heatmap
Cluster lift heatmap
Block similarity matrix
Rank movement chart
Calendar impact summary
Representative cluster gallery

The public website should use static JSON only.


---

13. Static JSON Output Design

The static build should generate files such as:

public/api/stats.json
public/api/vision-summary.json
public/api/image-attributes.json
public/api/clusters.json
public/api/voting-block-summary.json
public/api/voting-block-attribute-lift.json
public/api/voting-block-cluster-lift.json
public/api/voting-block-score-impact.json
public/api/voting-block-calendar-impact.json

These files should contain aggregate/reporting data only.

No raw voter-level records should be published.


---

14. Pipeline Design

14.1 Full Local Pipeline

Recommended full pipeline:

1. Load image inventory
2. Run local vision tagging
3. Generate image attributes
4. Generate image embeddings
5. Cluster images
6. Summarize clusters
7. Validate/review low-confidence labels
8. Load voting-block config
9. Generate synthetic voters
10. Generate synthetic votes
11. Compute vote statistics
12. Compute block-aware statistics
13. Compute bias detection
14. Compute calendar impact
15. Export static JSON
16. Build static website

14.2 Incremental Pipeline

The system should allow partial reruns:

artemis vision tag-images --changed-only
artemis vision embed-images --changed-only
artemis vision cluster-images --reuse-embeddings
artemis votes generate-blocks --config ...
artemis stats compute-block-analysis --scenario ...
artemis static build

14.3 Pipeline Outputs

Recommended output folders:

outputs/vision/
outputs/clusters/
outputs/voting_blocks/
outputs/stats/
outputs/static_api/
outputs/review/


---

15. CLI Command Design

15.1 Vision Commands

artemis vision tag-images
artemis vision embed-images
artemis vision cluster-images
artemis vision summarize-clusters
artemis vision export-review

15.2 Voting Commands

artemis votes generate-blocks
artemis votes validate-block-config
artemis votes summarize-run

15.3 Stats Commands

artemis stats compute
artemis stats compute-block-analysis
artemis stats compute-calendar-impact
artemis stats export-static-json

15.4 Static Build Command

artemis static build

15.5 Combined Workflow Command

artemis pipeline run --profile biased-voting-analysis


---

16. Recommended Implementation Sequence

Phase 1: Audit and Alignment

Review existing code paths for:

vote generation
synthetic voters
image features
statistics
bias detection
static JSON generation
stats page rendering
CLI command structure

Output:

docs/artemis_bias_extension_audit.md

Phase 2: Attribute Vocabulary

Add the controlled image-attribute vocabulary.

Implement:

dim_image_attribute
feature_image_attribute
derived attribute rules
attribute confidence thresholds
manual override support

Output:

config/image_attributes.yaml

Phase 3: Local Vision Tagging

Add local image tagging.

Implement:

artemis vision tag-images
structured JSON label output
confidence scoring
review flags
model/run metadata

Output:

outputs/vision/image_attributes.json

Phase 4: Embeddings and Clustering

Add embeddings and clustering.

Implement:

artemis vision embed-images
artemis vision cluster-images
artemis vision summarize-clusters
cluster review output

Output:

outputs/clusters/image_clusters.json
outputs/review/cluster_review.md

Phase 5: Voting Block Config Schema

Add voting-block config schema and validation.

Implement:

config/voting_blocks/*.yaml
JSON schema or Pydantic validation
dry-run validation
image match-count summary

Output:

outputs/voting_blocks/config_validation_summary.json

Phase 6: Voting Block Generator

Add local/admin generation.

Implement:

artemis votes generate-blocks
synthetic voter assignment
attribute-based utility function
vote generation
synthetic run metadata

Output:

outputs/voting_blocks/generated_vote_summary.json

Phase 7: Block-Aware Statistics

Add block-level marts and calculations.

Implement:

attribute lift
cluster lift
block similarity
score impact
calendar impact
bias detection status

Output:

outputs/stats/voting_block_analysis.json

Phase 8: Static API Export

Generate static reporting JSON.

Implement:

vision-summary.json
clusters.json
voting-block-summary.json
voting-block-attribute-lift.json
voting-block-cluster-lift.json
voting-block-score-impact.json
voting-block-calendar-impact.json

Phase 9: Static Website Update

Extend the stats page.

Implement:

Voting Bias Analysis section
Vision Label Summary section
Cluster Summary section
Attribute Lift chart
Cluster Lift chart
Block Similarity matrix
Score Impact section
Calendar Impact section

Do not add admin controls.

Phase 10: Acceptance Tests

Add known synthetic scenarios:

Earth+Moon preference block
Earth-only preference block
Moon+Sun preference block
Neutral control group
Random voters
Low-confidence label case
Small matching-image-count case

Acceptance criteria:

The CLI generates expected voter counts.
The CLI generates expected vote counts.
Attribute rules match expected images.
Biased blocks produce measurable attribute lift.
Cluster lift is calculated.
Score impact is calculated.
Static JSON is generated.
The public stats page displays aggregate results.
The public stats page exposes no generation controls.


---

17. Acceptance Criteria

The work is complete when:

1. Local vision tagging identifies Artemis-relevant attributes for each image.


2. Images are clustered and each cluster has a readable label.


3. Voting-block configs can define groups such as:



25 Earth+Moon voters
20 Earth-only voters
30 Moon+Sun voters

4. CLI commands can generate biased voting blocks locally.


5. Voting-block generation writes synthetic run metadata.


6. Statistical analysis calculates:



selection rate
attribute lift
cluster lift
block similarity
score impact
rank movement
calendar impact
bias detection status

7. Static JSON files are generated.


8. The static website displays aggregate voting-bias analysis.


9. The static website does not expose:



voter generation controls
admin forms
raw voter records
raw vote traces
model prompts
local paths
random seeds
pipeline execution controls

10. The system can be rerun with different local/admin configs without changing public-site code.




---

18. Summary

The Artemis project should be extended into a controlled local analysis system for synthetic voting bias.

The local/admin pipeline should identify image attributes using local vision models, cluster images by visual and semantic similarity, generate configurable biased voter groups, calculate block-aware statistical effects, and export read-only static analysis.

The public Artemis website should display the results: cluster groups, image labels, voting-block summaries, attribute lift, cluster lift, score impact, and calendar impact.

The public website should not become an admin tool. All generation and configuration should remain local, CLI-driven, and pipeline-controlled.