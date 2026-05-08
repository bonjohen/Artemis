# Lesson 040: Controlled Vocabulary as Schema Contract

## Problem

The vision tagging pipeline needs a consistent set of image attributes shared across five components: the vision model prompt, the attribute parser/validator, the database schema, the voting block config, and the cluster labeling engine. If any component uses an attribute code the others don't recognize — or spells it differently — the pipeline silently drops data or produces incorrect joins.

## Why It Matters

In a multi-stage pipeline where upstream output becomes downstream input, the attribute names are a de facto schema. Without a single source of truth, each stage invents its own list: the model prompt might say "earth_visible," the parser expects "earth," and the voting config references "Earth." These mismatches don't cause errors — they cause silent data loss, because a confidence score for "earth_visible" simply won't match any voting rule that checks for "earth."

## What Happened

1. Defined a YAML config (`config/image_attributes.yaml`) with two sections: `base_attributes` (22 codes assigned by the vision model) and `derived_attributes` (4 codes computed from base attribute combinations).
2. Each base attribute has `code`, `label`, `description`, and `type`. The `code` is the canonical identifier; `label` is for display; `description` becomes part of the VLM prompt; `type` groups attributes semantically (celestial_body, environment, hardware, crew, etc.).
3. The `AttributeVocabulary` dataclass loads this YAML and enforces invariants at load time: no duplicate codes, derived rules reference only existing base codes, thresholds are consistent.
4. The VLM prompt is generated from `vocab.base_attributes` — each attribute's code and description are injected into the prompt template. This means the prompt and the parser always agree on which codes exist.
5. Voting block configs (`config/voting_blocks/*.yaml`) reference attribute codes in `all_of`, `any_of`, `none_of` rules. The `validate_voting_config` function checks every referenced code against `vocab.all_codes` and rejects unknown references.
6. Derived attributes use boolean rules: `earth_and_moon` requires `all_of: [earth, moon]`. The `compute_derived_labels` method evaluates these rules against base confidence scores, applying the accepted/tentative thresholds consistently.

## Design Choice: YAML Config Over Code Constants or DB Schema

### Why YAML

- **Readable by non-developers.** A domain expert reviewing which attributes the system tracks can read the YAML without understanding Python.
- **Single file, single diff.** Adding an attribute means editing one YAML file. The change propagates to the prompt, parser, validator, and downstream consumers automatically through the `AttributeVocabulary` class.
- **Validation at load time.** The `load_attribute_vocabulary` function catches duplicate codes, invalid derived rules, and missing references before any pipeline stage runs. Compare to code constants scattered across modules, where a typo in one file might not surface until runtime.

### Why derived attributes are rules, not model outputs

Derived attributes like `earth_and_moon` (requires both Earth and Moon to be accepted) could be asked of the VLM directly. But:
- The VLM might disagree with its own base labels (says "earth_and_moon" is absent but "earth" and "moon" are both present).
- Computing derived labels from base confidences is deterministic and auditable.
- Adding new derived attributes doesn't require re-running the model on all images.

### Threshold design

Two thresholds (`accepted: 0.80`, `tentative: 0.50`) create a three-tier classification. The accepted threshold is deliberately high — VLMs are overconfident, so a 0.80 cutoff filters out weak associations while keeping genuine detections. The tentative band captures borderline cases that might be useful for analysis but shouldn't drive voting block membership.

## Key Insights

- **A controlled vocabulary is a schema contract between pipeline stages.** It prevents the most common integration bug in multi-stage pipelines: mismatched identifiers between producer and consumer.
- **Generate prompts from the same config that validates outputs.** If the VLM prompt lists attributes from the vocabulary, and the parser validates against the same vocabulary, the prompt and parser can never disagree on which codes exist.
- **Validate references across config files at load time, not at use time.** The voting block validator checks attribute codes against the vocabulary before any votes are generated. A typo in a block config is caught immediately, not after an hour of synthetic vote generation.
- **Derived attributes should be deterministic functions of base attributes.** Computing `earth_and_moon` from base scores means the derivation is auditable, reproducible, and doesn't require re-running the model. It also means derived attributes can be added retroactively to already-tagged images.
- **Type fields enable semantic grouping without coupling.** The `type` field on base attributes (celestial_body, crew, hardware, etc.) enables grouping in UIs and reports without any component depending on specific type values. New types can be added without code changes.

## Applicability

This pattern applies to any pipeline where labels or categories flow through multiple stages:
- NLP entity types shared between extraction, validation, and aggregation
- Taxonomy-based classification in content management systems
- Feature names in ML feature stores shared between extraction and model training

Does NOT apply when:
- The vocabulary is truly open-ended (free-text tags, user-generated labels)
- There's a single stage that both produces and consumes the labels
- The vocabulary changes faster than the pipeline can redeploy

## Related Lessons

- [Lesson 039: Mock Tagger for Vision Pipeline Testing](039_mock_tagger_for_vision_pipeline_testing.md) — the mock tagger uses `vocab.base_attributes` to generate deterministic scores, so the vocabulary contract is load-bearing for testing too
- [Lesson 027: Migration Ordering and Apply-on-Use](../block3/027_migration_ordering_and_apply_on_use.md) — the DB schema must match the vocabulary; migration 009 creates columns that align with the vocabulary's structure
