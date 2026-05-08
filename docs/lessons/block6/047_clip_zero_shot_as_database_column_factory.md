# Lesson 047: CLIP Zero-Shot as a Database Column Factory

## The Lesson

A single CLIP model, used for zero-shot classification against descriptive text prompts, functions as a general-purpose column generator for structured databases. Each new prompt produces a new confidence column — no training, no fine-tuning, no labeled data. The cost of adding a column is one forward pass over the image collection, and the only tuning knobs are the prompt template and the logit-to-confidence mapping.

## Context

A 12,217-image space photography collection needed structured content labels for calendar selection: which images show Earth, the Moon, spacecraft, crew, etc. The project already had CLIP embeddings (512-dim, openai/clip-vit-base-patch32) computed for clustering. The question was how to turn these embeddings into queryable, filterable database columns without training a custom classifier for each attribute.

## What Happened

1. Tested CLIP zero-shot classification against 5 labels on a single image. The model correctly identified "moon" with 0.959 confidence using softmax over all labels. But softmax across N labels produces a probability distribution that sums to 1 — adding more labels dilutes each score, making thresholds unstable.

2. Switched to independent per-attribute scoring: compute CLIP logits (cosine similarity × temperature) for all prompts at once, then apply a sigmoid transform to convert each logit to an independent [0,1] score. This decouples attributes — adding "hand" doesn't change the score for "moon."

3. Discovered that CLIP logits are domain-specific. For Artemis space photos, logits ranged 16–32 with mean ~24. A naive sigmoid centered at 0 would classify everything as "accepted." Analyzed the logit distribution across 50 images and 29 attributes to find the right sigmoid center (25.5) and scale (1.5).

4. Wrapped each attribute's description in a prompt template (`"a photo of {description}"`) to leverage CLIP's training distribution. The description comes from the YAML vocabulary file, so adding a new attribute means adding one YAML entry and re-running the tagger.

5. Tagged all 12,217 images against 29 attributes in 5 minutes on CPU (40 img/s, batch size 64). Added 8 more attributes incrementally — same speed, no need to re-tag existing attributes.

6. The result: 37 base attributes × 12,217 images = 451,829 confidence scores in `feature_image_attribute`, each queryable by code, threshold, and source. Derived attributes (earth_and_moon, spacewalk, etc.) computed from base scores using boolean rules.

## Key Insights

- **Zero-shot is free labeling at scale.** Traditional classifiers need labeled training data per category. CLIP's text-image alignment means any English phrase becomes a classifier. The "training data" is the prompt description — iterate on the description, not on a dataset.
- **Independent sigmoid beats shared softmax.** Softmax forces attributes to compete: raising one lowers others. Sigmoid treats each attribute independently, which matches reality — an image can show both Earth and the Moon. The tradeoff is that you need domain-calibrated sigmoid parameters instead of getting normalized probabilities for free.
- **The prompt template matters more than the model.** `"a photo of Earth visible in the image"` outperforms bare `"Earth"` because CLIP was trained on image-caption pairs, not image-keyword pairs. The template bridges the gap between database column names and CLIP's training distribution.
- **Logit distributions are domain-specific.** Space photography has a different logit landscape than ImageNet. The sigmoid center (25.5 for Artemis) must be empirically calibrated by examining the logit histogram on a sample of your actual images. A universal threshold doesn't exist.
- **The vocabulary file IS the model specification.** Adding `hand: "Human hand visible in the image"` to a YAML file and running the tagger produces a new database column with confidence scores. No code changes, no retraining, no deployment. This makes the vocabulary iteratively refinable by domain experts who don't write code.

## Examples

### Adding a new attribute

Before (YAML):
```yaml
base_attributes:
  - code: earth
    label: Earth
    description: Earth visible in the image
    type: celestial_body
```

After (add one entry):
```yaml
  - code: porthole
    label: Porthole
    description: Spacecraft window or porthole frame visible
    type: environment
```

Run incremental tagger → 688 images accepted for "porthole" → queryable immediately.

### Logit calibration

```
Attribute          min    mean   max    std
earth              22.8   30.0   31.7   2.6    ← strong signal
mission_control    16.6   18.7   20.6   0.9    ← weak signal
photograph         22.6   24.8   26.0   0.9    ← ambiguous
```

Sigmoid at center=25.5, scale=1.5 maps these to:
- earth: 0.95+ (accepted for most images)
- mission_control: <0.01 (rejected for all)
- photograph: ~0.50 (tentative — CLIP is unsure)

## Applicability

This approach works when:
- You need structured labels for a large image collection and can't afford per-category training
- The categories are describable in natural language (CLIP understands English, not domain codes)
- Approximate labels with confidence scores are acceptable (CLIP is not 100% accurate)
- The collection has a coherent visual domain (allowing sigmoid calibration)

Does NOT apply when:
- Fine-grained distinctions are needed that CLIP can't resolve (e.g., species-level bird classification)
- The labels require domain expertise that CLIP lacks (e.g., medical diagnosis from imaging)
- Exact precision/recall targets must be met (CLIP's zero-shot accuracy varies by category)

## Related Lessons

- [Lesson 040: Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) — the YAML vocabulary that drives CLIP tagging also validates downstream consumers
- [Lesson 039: Mock Tagger for Vision Pipeline Testing](039_mock_tagger_for_vision_pipeline_testing.md) — hash-based mock tagger exercises the same confidence-threshold logic without CLIP
- [Lesson 046: Lazy Imports for Deployment Compatibility](046_lazy_imports_for_deployment_compatibility.md) — CLIP's numpy/torch dependencies must be lazy-imported for CI and static builds
- [Lesson 051: Sigmoid Calibration for Domain-Specific CLIP](051_sigmoid_calibration_for_domain_specific_clip.md) — the sigmoid transform that converts CLIP logits to queryable confidence scores
- [Lesson 052: Incremental Feature Extraction](052_incremental_feature_extraction.md) — the incremental mode that adds new vocabulary columns without re-tagging existing ones
