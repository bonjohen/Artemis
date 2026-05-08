# Lesson 052: Incremental Feature Extraction Over Full Re-runs

## The Lesson

When adding new features to an existing collection, delete-and-rewrite only the new columns rather than re-processing everything. The key enabler is tagging each row with its source (model version, label source, attribute code) so that surgical deletes and inserts are possible without touching existing data.

## Context

A CLIP zero-shot tagger had classified 12,217 images against 29 attributes, producing 354,293 rows in `feature_image_attribute`. The user wanted to add 8 new attributes (hand, porthole, full_earth, etc.) without re-running the full 5-minute tagging pass and without losing the existing 29 attributes' scores.

## What Happened

1. The original `tag_all_images()` function did a blanket delete: `DELETE FROM feature_image_attribute WHERE label_source = 'clip_zero_shot'` followed by a full re-tag of all images against all attributes. Simple but wasteful — the 29 existing attributes' scores hadn't changed.

2. Built `tag_new_attributes(conn, vocab, attribute_codes)` that:
   - Accepts a list of specific attribute codes to tag
   - Deletes only rows matching those codes: `DELETE WHERE attribute_code = ? AND label_source = 'clip_zero_shot'`
   - Builds CLIP prompts only for the specified codes
   - Iterates all images but writes only the subset of attribute scores
   - Identifies derived attributes whose rules reference the new codes and recomputes only those

3. Added auto-detection mode: when `attribute_codes=None`, queries the database for which vocabulary codes have zero rows in `feature_image_attribute` and tags only those. This makes the workflow: add entries to YAML → run tagger → new columns appear.

4. The incremental run for 8 new attributes took 5 minutes — the same wall-clock time as a full run, because the bottleneck is CLIP inference over 12,217 images, not the number of attributes (all prompts are processed in one forward pass). But the incremental approach preserved the existing 354,293 rows untouched — no risk of data loss, no unnecessary database churn.

5. For derived attributes, the function loads existing base confidence scores from the database and merges them with the newly computed scores before evaluating derivation rules. This correctly handles cases like `earth_through_porthole = all_of: [earth, porthole]` where `earth` scores already exist and only `porthole` is new.

## Key Insights

- **Tag every row with its provenance.** The `label_source` ('clip_zero_shot', 'derived_rule') and `attribute_code` columns enable surgical deletes. Without them, the only option is "delete everything and re-insert" — the batch-processing anti-pattern.
- **Auto-detection eliminates manual bookkeeping.** Querying "which codes are in the vocabulary but have zero rows?" means the user doesn't need to remember which attributes were already tagged. The system figures out what's missing.
- **Incremental ≠ faster per-image.** CLIP processes all prompts in one forward pass, so 8 prompts and 37 prompts have nearly the same per-image cost. The value of incremental is preserving existing data, not speed. If the per-attribute cost were linear (e.g., a model that processes one attribute at a time), incremental would also be faster.
- **Derived attributes need merge logic.** A derived attribute like `earth_through_porthole` depends on both `earth` (existing) and `porthole` (new). The incremental tagger must load existing base scores and merge with new scores before evaluating derivation rules. Skipping this step would produce incorrect derived labels.
- **The vocabulary file is the single source of truth for "what should exist."** Adding an attribute to `image_attributes.yaml` and running the tagger with `--incremental` guarantees the attribute gets tagged. Removing an attribute from the YAML doesn't auto-delete existing rows — that's intentional, preserving historical data.

## Applicability

Incremental feature extraction applies when:
- Features are stored in a denormalized table with a type/source column
- New feature types can be added without invalidating existing ones
- The extraction cost is per-image (not per-feature), making full re-runs wasteful of I/O even if not of compute
- The feature schema is defined in configuration, not code

Does NOT apply when:
- Features are interdependent (changing one feature's model invalidates all others)
- The extraction is cheap enough that full re-runs are simpler to reason about
- The feature store uses a columnar schema where each feature is a separate column (ALTER TABLE ADD COLUMN is the "incremental" path)

## Related Lessons

- [Lesson 047: CLIP Zero-Shot as a Database Column Factory](047_clip_zero_shot_as_database_column_factory.md) — the system that produces the features incrementally extracted here
- [Lesson 040: Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) — the vocabulary drives both what to extract and what's already present
- [Lesson 051: Sigmoid Calibration for Domain-Specific CLIP](051_sigmoid_calibration_for_domain_specific_clip.md) — the confidence calibration applied to both full and incremental tagging runs
