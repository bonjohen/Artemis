# Lesson 044: Acceptance Tests as Executable Specifications

## Problem

The biased voting blocks pipeline spans six components: config validation, vote generation, attribute analysis, cluster analysis, score/calendar impact, and static export. Unit tests cover each component in isolation, but the interesting behaviors — "does a biased block produce detectable lift in the analysis output?" — are emergent properties of the full pipeline. Integration tests are needed, but writing them naively leads to either brittle exact-value assertions or meaningless "it didn't crash" tests.

## Why It Matters

A pipeline with 6 components and 13 new database tables has a large surface for integration bugs: wrong join keys, mismatched scenario IDs, empty result sets from missing data, off-by-one errors in voter/ballot counts. Unit tests can't catch these because they mock the boundaries where the bugs live. But integration tests that assert exact output values are fragile — any change to the utility function weights, random seed, or attribute distribution breaks them. The right approach is testing *structural properties* that hold across a range of parameter values.

## What Happened

1. Built a `full_pipeline_db` pytest fixture that constructs an in-memory DuckDB with all 9 migration files applied, seeds 100 images (25 Earth+Moon, 25 Earth-only, 10 Moon+Sun, 40 no-attributes), creates 5 visual clusters, generates block votes from a 4-block config, and runs the full analysis pipeline. The fixture returns the connection and scenario ID.
2. Chose deliberately small block sizes (5, 4, 6, 10 voters × 10 votes each = 250 ballots) to keep the fixture fast (<2 seconds) while still producing enough data for statistical signal.
3. Wrote property-based assertions instead of exact-value assertions:
   - `test_voter_counts_per_block`: asserts exact counts because voter assignment is deterministic
   - `test_vote_counts_generated`: asserts total ballot count (250 = 25 voters × 10 votes)
   - `test_attribute_lift_measurable`: asserts lift > 1.0 for Earth attribute in the Earth+Moon block — a structural property that holds regardless of exact utility values
   - `test_detection_status_assigned`: asserts 4 statuses exist and neutral block is "not_applicable"
   - `test_no_admin_controls`: asserts PII-like strings are absent from exported JSON
4. Separated config validation tests (`TestConfigValidation`) from pipeline tests (`TestVoterGeneration`, `TestBiasDetection`, `TestStaticExport`). Config tests don't need the full pipeline fixture and run against the real YAML file on disk.
5. The dry-run test (`TestDryRun`) verifies image counts against the planted attribute distribution: 25 images match Earth+Moon rules, 25 match Earth-only rules, 10 match Moon+Sun rules, 100 match neutral. These are exact because the test data is deterministic.

## Design Choice: Property Assertions Over Exact Value Assertions

### Why assert `lift > 1.0` instead of `lift == 2.47`

The exact lift value depends on: the random seed, the number of voters, the utility function weights, the noise sigma, and the attribute distribution. Changing any of these (which is expected during tuning) would break an exact assertion. But the *property* — "a biased block produces lift above 1.0 for its target attribute" — is invariant. It holds across all reasonable parameter combinations. If it doesn't hold, something is genuinely broken.

### Why test voter counts exactly

Unlike lift, voter counts are deterministic: `voter_count=5` in the config means exactly 5 voters are created. There's no noise or randomness in voter assignment. Asserting exact counts here catches off-by-one errors and double-insertion bugs, which are real risks in a pipeline that creates voters, assigns them to blocks, and then generates ballots in nested loops.

### Why a single large fixture instead of per-test setup

The full pipeline takes ~1 second to construct. Running it once and sharing the connection across all tests in a class (`full_pipeline_db` fixture) keeps the suite fast. The tradeoff is that tests aren't fully isolated — a test that modifies the DB could affect later tests. In practice, this doesn't happen because all tests are read-only queries against the analysis outputs.

## Key Insights

- **Assert structural properties, not computed values, for probabilistic pipelines.** "Lift > 1.0 for the biased block's target attribute" is a property. "Lift = 2.47" is a value. Properties survive parameter changes; values don't. Reserve exact assertions for deterministic quantities (voter counts, image counts, ballot counts).
- **The fixture IS the specification.** The `full_pipeline_db` fixture documents the data contract: 100 images with specific attribute distributions, 4 blocks with specific rules, exact voter and ballot counts. Any developer reading the fixture understands exactly what data the tests assume. This is more reliable than a prose spec.
- **Dry-run tests bridge config and runtime.** The dry-run test loads the real YAML config and checks image counts against the test data. It verifies that the SQL-based image matching in `dry_run()` agrees with the manually seeded attributes. This catches bugs where the SQL conditions don't match the intent of the config rules.
- **Test PII absence with string matching, not schema inspection.** Checking `"voter_sk" not in content` is more robust than checking the JSON schema, because it catches PII that leaks through serialization artifacts, error messages, or nested structures that schema checks might miss.
- **Small-scale fixtures are fast and sufficient.** 100 images, 25 voters, 250 ballots — enough data to produce statistical signal (lift > 1.0) but small enough to run in <2 seconds. The fixture doesn't need to mimic production scale to test pipeline correctness.
- **Separate deterministic tests from statistical tests.** Config validation and voter counts are deterministic — assert exact values. Bias detection and lift are statistical — assert properties. Mixing the two styles in a single test makes failures ambiguous.

## Applicability

This pattern applies to any pipeline that transforms data through multiple stages where the output has both deterministic and probabilistic components:
- ETL pipeline testing (deterministic row counts, statistical quality metrics)
- ML pipeline testing (deterministic preprocessing, probabilistic model outputs)
- Financial reconciliation (exact ledger balances, approximate risk scores)

Does NOT apply when:
- The pipeline is fully deterministic (use exact assertions everywhere)
- The pipeline output is opaque (e.g., a trained model) and requires specialized evaluation
- Tests must run against production data (fixtures are inapplicable)

## Related Lessons

- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — the full-pipeline fixture is a self-contained synthetic environment; this lesson extends the principle to testing strategy
- [Lesson 029: Ground-Truth Recovery as Validation](../block4/029_ground_truth_recovery_as_validation.md) — the acceptance tests verify that planted biases (ground truth) are recovered by the analysis pipeline
- [Lesson 039: Mock Tagger for Vision Pipeline Testing](039_mock_tagger_for_vision_pipeline_testing.md) — the acceptance tests bypass the tagger entirely with direct DB seeding, a complementary strategy to mocking
- [Lesson 043: PII Sanitization in Static Exports](043_pii_sanitization_in_static_exports.md) — the `test_no_admin_controls` test is the acceptance-test layer of the PII defense-in-depth strategy
