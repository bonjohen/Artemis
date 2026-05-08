# Lesson 039: Mock Tagger Pattern for Vision Pipeline Testing

## Problem

The vision tagging pipeline uses Qwen2.5-VL (a 7B-parameter vision-language model) to classify image attributes. Running the real model requires a GPU, takes seconds per image, and produces non-deterministic outputs. The full pipeline — config loading, tagging, derived label computation, DB persistence, cluster labeling, voting block generation, bias analysis — needs to be testable in CI without any model infrastructure.

## Why It Matters

Vision-language models are expensive and slow. If every test that touches image attributes requires loading a 7B model, the test suite becomes unusable: minutes of GPU time per run, flaky results from non-deterministic generation, and CI runners without GPU support can't run the tests at all. But if you test everything *except* the model, you miss integration bugs between the model output format and the downstream pipeline. The mock must produce structurally valid outputs that exercise the same code paths as real model outputs.

## What Happened

1. Built `VisionTagger` as the real tagger: loads Qwen2.5-VL lazily on first use, sends a structured prompt listing all attribute codes with descriptions, parses JSON output, validates against the `AttributeVocabulary`, and returns `{code: confidence}` dicts.
2. Built `MockTagger` as a parallel implementation with the same interface (`tag_image`, `tag_batch`). Instead of running a model, it hashes the filename with SHA-256 and maps hash bytes to deterministic confidence scores for each attribute code.
3. The hash-based approach means: (a) the same filename always produces the same attributes, making tests deterministic; (b) different filenames produce different attribute distributions, so tests can reason about which images have which labels; (c) the confidence scores spread across the full 0.0–1.0 range, exercising accepted/tentative/rejected classification logic.
4. Both taggers produce the same output type (`dict[str, float]`), so all downstream code — `compute_derived_labels`, `compute_accepted_base_labels`, the DB loader, cluster labeling, voting block matching — works identically with either tagger.
5. The acceptance test fixture (`full_pipeline_db`) bypasses the tagger entirely and inserts attributes directly into `feature_image_attribute`, because the test needs *controlled* attribute assignments (exactly images 1–25 have Earth+Moon) rather than hash-derived ones. This is a third strategy: direct DB seeding for scenario-specific tests.

## Design Choice: Hash-Based Determinism Over Random or Fixture

### Why hash the filename

Three alternatives were considered:

- **Random attributes:** Non-deterministic — tests would pass or fail depending on the random seed, making failures hard to reproduce.
- **Fixed fixture data:** Deterministic but brittle — adding a new attribute to the vocabulary breaks the fixture, and the fixture doesn't exercise the confidence-threshold classification logic across the full range.
- **Hash-based:** Deterministic, self-scaling (new attributes automatically get scores from unused hash bytes), and exercises the full confidence range without manual curation.

### Why three testing strategies coexist

1. `MockTagger` — for unit tests of the tagging pipeline itself (prompt building, output parsing, vocabulary validation).
2. Direct DB seeding — for acceptance tests that need specific attribute distributions (25 Earth+Moon images, 25 Earth-only, etc.) to verify bias detection at known thresholds.
3. Real `VisionTagger` — for manual validation only, never in CI.

Each strategy serves a different testing need. Collapsing to a single strategy would either make tests slow (real model) or unable to test controlled scenarios (mock only).

## Key Insights

- **Mock at the model boundary, not the pipeline boundary.** The `MockTagger` replaces only the model inference, preserving all prompt construction, output parsing, vocabulary validation, and confidence classification logic. A mock that replaced the entire pipeline would miss bugs in these layers.
- **Hash-based mocks are self-maintaining.** When the attribute vocabulary grows from 22 to 30 attributes, the `MockTagger` automatically generates scores for the new attributes from the next hash bytes. No fixture updates needed.
- **Deterministic scores must span the full range.** SHA-256 bytes divided by 255 produce values from 0.0 to 1.0 uniformly. This means every test run exercises the `accepted` (>= 0.80), `tentative` (0.50–0.79), and `rejected` (< 0.50) code paths for different attributes on different images. A mock that always returned 0.90 would never test tentative or rejected handling.
- **Direct DB seeding is the right mock for scenario tests.** When you need "exactly 25 images with attribute X," constructing that through a mock tagger adds indirection. Inserting rows into `feature_image_attribute` directly is clearer, faster, and makes the test's data assumptions explicit.
- **Lazy model loading prevents import-time failures.** `VisionTagger._load_model()` runs on first `tag_image()` call, not at `__init__`. This means importing the module never triggers a GPU check, so the mock path doesn't need special import guards.

## Applicability

This pattern applies whenever a pipeline includes an expensive, non-deterministic external component (ML model, API call, hardware sensor):
- Image classification, object detection, or captioning pipelines
- LLM-based data extraction with structured output
- Any system where the model output feeds into downstream validation, aggregation, or analysis

Does NOT apply when:
- The model's behavior *is* what you're testing (evaluation, fine-tuning experiments)
- The output format is trivial (a single scalar) — mocking adds overhead without value
- The model is fast and deterministic enough to run in CI directly

## Related Lessons

- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — the broader pattern of building and testing pipelines with known data before real data arrives
- [Lesson 029: Ground-Truth Recovery as Validation](../block4/029_ground_truth_recovery_as_validation.md) — acceptance tests verify that planted signals (attribute biases) are recovered, which requires controlled inputs
