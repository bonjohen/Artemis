# Lesson 051: Sigmoid Calibration for Domain-Specific CLIP Scores

## The Lesson

CLIP logits have domain-specific distributions. Converting them to meaningful [0,1] confidence scores requires a sigmoid transform calibrated to the actual logit range in your image collection. A universal threshold doesn't work — the sigmoid center and scale must be tuned empirically by examining logit histograms on a representative sample.

## Context

CLIP zero-shot classification was being used to tag 12,217 space photographs with 29 content attributes (earth, moon, deep_space, spacecraft, etc.). CLIP outputs logits — cosine similarity between image and text embeddings, scaled by a learned temperature (~100). These logits need to become [0,1] confidence scores with a threshold-based classification: accepted (≥ 0.80), tentative (0.50–0.79), rejected (< 0.50).

## What Happened

1. First attempt used softmax across all 29 attributes. This gave normalized probabilities summing to 1, but adding more attributes diluted every score. An image that was clearly "earth" scored 0.456 because the probability mass was spread across 29 categories. Thresholds were unstable — they'd need recalibration every time an attribute was added.

2. Second attempt used per-attribute binary classification: for each attribute, compare the attribute prompt against a generic negative ("a photo of something else entirely"). This gave independent scores but was 29× slower (one forward pass per attribute per batch) and the generic negative was too vague — CLIP gave high scores to almost everything.

3. Third attempt: compute all 29 logits in a single forward pass, then apply a sigmoid transform to each logit independently. This gives independent [0,1] scores without the softmax competition problem and without the 29× speed penalty.

4. But sigmoid with default center=0 classified everything as accepted, because CLIP logits for Artemis photos ranged 16–32, all far above zero.

5. Ran a calibration experiment: 50 diverse images, all 29 attributes, extracted raw logits. Found the distribution:
   - Strong matches (earth, atmosphere): logits 28–32
   - Moderate matches (spacecraft, rocket): logits 24–28
   - Weak matches (mission_control, diagram): logits 16–21
   - Per-attribute std: 0.9–3.1

6. Chose sigmoid center=25.5 and scale=1.5 based on the distribution:
   - Logit > 27 → score > 0.84 → "accepted"
   - Logit 24–27 → score 0.24–0.84 → "tentative"
   - Logit < 24 → score < 0.24 → "rejected"

7. Validated by inspecting per-cluster attribute counts. Earth-from-orbit images correctly got `earth`, `atmosphere`, `surface` as accepted. Dark space images got `deep_space`. Crew photos got `astronaut`. The thresholds separated genuine content from CLIP noise.

## Key Insights

- **Softmax is wrong for multi-label classification.** Images can be both "earth" and "moon." Softmax forces attributes to compete — the probability for "earth" goes down when "moon" is high. Independent sigmoids correctly model the multi-label nature of image content.
- **The sigmoid center is the most important hyperparameter.** It determines where the decision boundary falls in logit space. Too low → everything accepted. Too high → nothing accepted. The right center is the logit value that separates "present" from "absent" for a typical attribute on a typical image in your domain.
- **Calibrate on your data, not on ImageNet.** CLIP's logit distribution depends on image content, resolution, and prompt style. Space photographs produce different logit ranges than product photos or street scenes. A calibration sample of 50 images is sufficient to characterize the distribution.
- **Scale controls decision sharpness.** A small scale (1.0) produces sharp binary decisions — scores are near 0 or 1. A large scale (3.0) produces gradual confidence gradients. Scale=1.5 gives a useful tentative band where CLIP is uncertain, which is informative for borderline cases.
- **One forward pass for all attributes.** CLIP computes image-text similarity for all text prompts simultaneously. The sigmoid transform is element-wise on the logit matrix. Adding attributes costs nothing at inference time — only storage grows.

## Examples

### Logit distribution by attribute type

```
Attribute           min    mean   max    Decision at center=25.5
─────────────────────────────────────────────────────────────────
earth               22.8   30.0   31.7   Mostly accepted
atmosphere          21.5   29.3   31.4   Mostly accepted
deep_space          22.8   27.0   30.4   Mix of accepted/tentative
spacecraft          21.1   26.7   28.7   Mix of accepted/tentative
mission_control     16.6   18.7   20.6   Always rejected
diagram             17.3   19.0   23.3   Always rejected
```

### Sigmoid comparison

```
center=22, scale=3:  Too permissive — spacecraft accepted for every image
center=25.5, scale=1.5:  Clean separation — spacecraft accepted only for hardware images
center=28, scale=1.5:  Too strict — even clear earth images are only tentative
```

## Applicability

Sigmoid calibration applies when:
- Converting model logits to confidence scores for threshold-based decisions
- The logit distribution is domain-specific (not centered at zero)
- Multi-label classification is needed (attributes are independent)
- You need a "tentative" band between "yes" and "no"

Does NOT apply when:
- Logits are already calibrated (temperature-scaled models, Platt scaling applied)
- Binary classification with a single threshold is sufficient (use logistic regression instead)
- The decision boundary varies per attribute (use per-attribute thresholds instead of a shared sigmoid)

## Related Lessons

- [Lesson 047: CLIP Zero-Shot as a Database Column Factory](047_clip_zero_shot_as_database_column_factory.md) — the sigmoid is the bridge between CLIP logits and queryable database columns
- [Lesson 040: Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) — the vocabulary defines what attributes exist; the sigmoid defines how confidently they're assigned
- [Lesson 052: Incremental Feature Extraction](052_incremental_feature_extraction.md) — incremental tagging reuses the same sigmoid calibration for new attributes added to the vocabulary
