# Lesson 041: Utility Function Design for Synthetic Voting Bias

## Problem

Synthetic vote generation needs to produce votes that exhibit detectable attribute-based bias while remaining statistically plausible. A biased voter block that always votes for images with specific attributes produces trivially detectable (and unrealistic) bias. A block with too much noise produces undetectable bias. The utility function must allow precise control over bias strength relative to noise.

## Why It Matters

The bias detection pipeline can only be validated if the synthetic data contains known, tunable biases. If the utility function is too simple (binary: prefer or not), the resulting bias is either overwhelming or absent. If it's too complex (multi-factor interactions, non-linear preferences), the relationship between config parameters and observable bias becomes opaque, making it impossible to write meaningful acceptance tests.

## What Happened

1. Designed a three-component utility function: `utility = base_appeal + preference_weight * match_score + randomness_weight * noise`.
2. `base_appeal` is deterministic per image (SHA-256 hash of image SK + seed → float in [0, 1]). This gives every image a fixed "inherent quality" that all voters agree on, preventing purely random outcomes.
3. `match_score` measures how well an image matches a block's attribute rules. It uses `_compute_attribute_match`: +1 per satisfied `all_of` rule, +1 if any `any_of` rule matches, -0.5 penalty per violated `none_of` rule, normalized by max possible score.
4. `noise` is `rng.gauss(0, 0.3)` — Gaussian noise to simulate voter disagreement and attention variability.
5. The two weights (`preference_weight` and `randomness_weight`) control the balance. In the test config: biased blocks use `preference_weight=2.2–2.6` with `randomness_weight=0.30–0.40`, while the neutral control uses `preference_weight=0.0` with `randomness_weight=1.0`.
6. Initial testing showed that `preference_weight` needed to be well above 1.0 (2.0+) to produce detectable lift, because the match score is normalized to [0, 1] and the noise standard deviation of 0.3 can easily mask a small preference bump.
7. The `none_of` penalty is asymmetric (-0.5 instead of -1.0) because aversion is typically weaker than preference in real voting behavior — voters gravitate toward what they like more strongly than they avoid what they don't.

## Design Choice: Additive Utility Over Multiplicative or Threshold-Based

### Why additive

Three alternatives:
- **Multiplicative:** `base_appeal * (1 + preference_weight * match)`. Problem: images with low base appeal stay low regardless of preference, which means biased blocks still select similar images to neutral blocks — the bias is muted.
- **Threshold-based:** "If match > 0.5, always select." Problem: produces binary bias that's trivially detectable and unrealistic. Real voters have preferences, not rules.
- **Additive:** Each component contributes independently. A strong match can overcome low base appeal, and noise can occasionally override preference. The weights directly control how much each component matters.

### Why separate weights instead of a single bias strength

A single "bias strength" parameter would conflate two independent dimensions: how much the voter cares about attributes (preference) and how noisy their decisions are (randomness). Separating them allows the test config to express "strong preference but high noise" (partially detectable bias) separately from "weak preference but low noise" (subtle but consistent bias). This matters for testing detection sensitivity.

### Why Gaussian noise instead of uniform

Gaussian noise has tails — occasionally a voter makes an extreme choice. Uniform noise is bounded, which makes the utility function's behavior more predictable but less realistic. The sigma of 0.3 was chosen empirically: small enough that `preference_weight=2.5` dominates most decisions, large enough that the top-5 selection from a batch of 50 occasionally includes non-preferred images.

## Key Insights

- **Additive utility with separate weights gives orthogonal control.** `preference_weight` controls signal strength; `randomness_weight` controls noise amplitude. A test author can reason about each independently: "doubling preference_weight roughly doubles the lift" and "halving randomness_weight roughly halves the variance."
- **Base appeal prevents degenerate selections.** Without a shared quality signal, neutral voters select uniformly at random, and biased voters select only from their preferred pool. The base appeal creates a realistic quality gradient that all voters partially agree on, so biased voters select *mostly* from their preferred pool but with some overlap with neutral voters' picks.
- **Match score normalization to [0, 1] makes weights interpretable.** A `preference_weight` of 2.0 means "add up to 2.0 utility for a perfect match." Without normalization, the weight's meaning would depend on how many `all_of` rules a block has.
- **Asymmetric none_of penalty reflects real behavior.** Setting `none_of` to -0.5 instead of -1.0 means aversion is weaker than attraction. This matches empirical voting: people who prefer Earth images might slightly avoid deep-space images, but the avoidance is milder than the preference.
- **Empirical tuning of the preference-to-noise ratio is unavoidable.** Theory can guide the shape of the utility function, but the specific weight values that produce detectable-but-not-obvious bias depend on the batch size (50 shown, 5 selected), the number of voters per block, and the attribute distribution across images. The config YAML makes this tuning explicit and reproducible.

## Applicability

This utility function pattern applies to any synthetic data generation that needs controlled, tunable signal-to-noise ratios:
- A/B test simulators where treatment effect size must be parameterized
- Recommendation system evaluation with planted relevance signals
- Fraud detection testing with known fraudulent patterns at configurable rates

Does NOT apply when:
- You need to model strategic voting (utility functions assume sincere preferences)
- The voting mechanism is pairwise or ranked rather than batch selection (different noise model needed)
- Real voter behavior data is available and should be replayed rather than simulated

## Related Lessons

- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — the broader principle; this lesson covers the specific utility function design within synthetic generation
- [Lesson 028: Chi-Squared for Bias Detection](../block4/028_chi_squared_for_bias_detection.md) — the detection side of the same coin; the utility function plants bias, chi-squared tests detect it
- [Lesson 040: Controlled Vocabulary as Schema Contract](040_controlled_vocabulary_as_schema_contract.md) — the match score depends on attribute codes being consistent between the vocabulary, the config, and the DB
