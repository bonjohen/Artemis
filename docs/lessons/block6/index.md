# Block 6: Biased Voting Blocks & Vision Tagging Lessons

6 lessons from the biased voting blocks, vision tagging, block-aware statistics, and static reporting implementation.

| # | Lesson | Core Teaching |
|---|---|---|
| 039 | [Mock Tagger for Vision Pipeline Testing](039_mock_tagger_for_vision_pipeline_testing.md) | Hash-based mock tagger provides deterministic, self-scaling attribute generation for CI without GPU |
| 040 | [Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) | A single YAML vocabulary enforces attribute consistency across VLM prompt, parser, DB, config, and analysis |
| 041 | [Utility Function for Synthetic Voting Bias](041_utility_function_for_synthetic_voting_bias.md) | Additive utility (base appeal + preference × match + randomness × noise) gives orthogonal control over bias strength |
| 042 | [Lift as the Primary Bias Detection Metric](042_lift_as_primary_bias_metric.md) | Lift (block rate / global rate) is scale-invariant and base-rate-invariant, making it the right primary metric for bias detection |
| 043 | [PII Sanitization in Static Exports](043_pii_sanitization_in_static_exports.md) | Defense in depth — query exclusion, recursive field stripping, and post-export content scanning — prevents PII leaks in public JSON |
| 044 | [Acceptance Tests as Executable Specifications](044_acceptance_tests_as_executable_specifications.md) | Assert structural properties (lift > 1.0) for statistical outputs and exact values for deterministic outputs |
