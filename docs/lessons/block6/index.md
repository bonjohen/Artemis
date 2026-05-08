# Block 6: Biased Voting Blocks, Vision Tagging & Image Curation Lessons

15 lessons from biased voting blocks, vision tagging, CLIP classification, image deduplication, and interactive selection tooling.

| # | Lesson | Core Teaching |
|---|---|---|
| 039 | [Mock Tagger for Vision Pipeline Testing](039_mock_tagger_for_vision_pipeline_testing.md) | Hash-based mock tagger provides deterministic, self-scaling attribute generation for CI without GPU |
| 040 | [Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) | A single YAML vocabulary enforces attribute consistency across VLM prompt, parser, DB, config, and analysis |
| 041 | [Utility Function for Synthetic Voting Bias](041_utility_function_for_synthetic_voting_bias.md) | Additive utility (base appeal + preference x match + randomness x noise) gives orthogonal control over bias strength |
| 042 | [Lift as the Primary Bias Detection Metric](042_lift_as_primary_bias_metric.md) | Lift (block rate / global rate) is scale-invariant and base-rate-invariant for bias detection |
| 043 | [PII Sanitization in Static Exports](043_pii_sanitization_in_static_exports.md) | Defense in depth — query exclusion, recursive field stripping, and post-export content scanning |
| 044 | [Acceptance Tests as Executable Specifications](044_acceptance_tests_as_executable_specifications.md) | Assert structural properties for statistical outputs and exact values for deterministic outputs |
| 045 | [Embedding Deduplication for Image Curation](045_embedding_deduplication_for_image_curation.md) | CLIP cosine similarity + connected components reduced 12,217 images to 2,163 unique representatives |
| 046 | [Lazy Imports for Deployment Compatibility](046_lazy_imports_for_deployment_compatibility.md) | Move heavy dependencies (numpy, torch) to function scope so lightweight deployments don't break |
| 047 | [CLIP Zero-Shot as a Database Column Factory](047_clip_zero_shot_as_database_column_factory.md) | One CLIP model + descriptive prompts = arbitrarily many structured database columns, no training needed |
| 048 | [Greedy Max-Min Diversity Selection](048_greedy_max_min_diversity_selection.md) | Iteratively pick the most distant item from selected set — O(n*k), near-optimal, 15 lines of code |
| 049 | [Drag-and-Drop as Simplest Viable Interaction](049_drag_and_drop_as_simplest_viable_interaction.md) | Co-visible source pool + target slots with HTML5 DnD beats modals, search, and multi-step wizards |
| 050 | [Connected Components for Transitive Dedup](050_connected_components_for_transitive_dedup.md) | scipy sparse graph components correctly group transitive chains that pair-based merging splits |
| 051 | [Sigmoid Calibration for Domain-Specific CLIP](051_sigmoid_calibration_for_domain_specific_clip.md) | CLIP logits are domain-specific (16-32 for space photos); sigmoid center and scale must be empirically tuned |
| 052 | [Incremental Feature Extraction](052_incremental_feature_extraction.md) | Delete-and-rewrite only new attribute codes; label_source and attribute_code columns enable surgical updates |
| 053 | [Audit-First Design](053_audit_first_design.md) | A 15-minute written audit of existing code prevents hours of reimplementation and identifies extension points |
