# Lesson 042: Lift as the Primary Bias Detection Metric

## Problem

Block-aware statistics need a metric that answers: "does this voting block select images with attribute X more than expected?" Raw selection counts don't work because blocks have different sizes. Rate differences (block rate - global rate) are hard to interpret when base rates vary widely. The metric needs to be intuitive, comparable across attributes, and actionable for the detection classifier.

## Why It Matters

The bias detection system classifies each voting block as `detected`, `partially_detected`, `inconclusive`, or `not_detected` based on statistical evidence. The classification metric must be scale-invariant (a block of 5 voters compared against a pool of 25), attribute-invariant (rare attributes with 2% base rate compared against common attributes with 40% base rate), and threshold-friendly (clean cutoffs for classification tiers). The wrong primary metric leads to either missed biases or false alarms.

## What Happened

1. Computed per-block, per-attribute selection rates: `block_selection_rate = block_selected / block_exposed` and `global_selection_rate = global_selected / global_exposed`. These are vote-level rates, not distinct-image rates, because the same image can appear in multiple ballots.
2. Computed lift as `block_rate / global_rate`. Lift = 1.0 means no bias; lift = 2.0 means the block selects this attribute at twice the global rate.
3. Added odds ratio as a secondary metric: `(a * d) / (b * c)` from a 2x2 table (selected/not × block/not-block). The odds ratio is less intuitive but more statistically robust for rare events.
4. Added Wilson confidence intervals for the block selection rate to quantify uncertainty. The Wilson interval is preferred over the normal approximation because it handles rates near 0 or 1 correctly and never produces negative bounds.
5. Set detection thresholds on *average lift across target attributes*: >= 2.0 = detected, >= 1.3 = partially_detected, >= 1.1 = inconclusive, < 1.1 = not_detected. These thresholds were tuned against the synthetic test config where `preference_weight=2.5` reliably produces average lift above 2.0.
6. Also computed cluster-level lift (block cluster selection rate vs. global cluster rate) with chi-squared contribution per cell. This shows whether bias flows through to cluster-level distortion.

## Design Choice: Lift Over Rate Difference or Statistical Tests

### Why lift, not rate difference

Rate difference (`block_rate - global_rate`) is additive. An attribute with 2% global rate and 4% block rate has a +2% difference. An attribute with 40% global rate and 42% block rate also has a +2% difference. But the first case is a 2x increase (lift = 2.0) while the second is a 5% increase (lift = 1.05). Lift captures relative change, which is what matters for bias detection — a block that doubles the selection of a rare attribute is more noteworthy than one that barely increases a common attribute.

### Why not use p-values as the primary metric

Chi-squared p-values from block 4's bias detection (Lesson 028) answer "is there *any* non-uniformity?" but don't quantify *how much* bias. A block with 1000 voters might show p < 0.001 for a lift of 1.02 (statistically significant but practically irrelevant). Lift directly answers "how much more?" which maps cleanly to detection tiers.

### Why Wilson intervals, not normal approximation

The Wilson interval is more reliable at small sample sizes and extreme proportions. With 5 voters × 10 ballots × 50 images = 2500 exposures per block, sample size isn't tiny, but some attributes appear in only a fraction of images, creating small effective samples. The Wilson interval handles these gracefully without requiring minimum-sample-size guards.

## Key Insights

- **Lift is scale-invariant and base-rate-invariant.** A lift of 2.0 means "twice the expected rate" regardless of whether the base rate is 1% or 50%. This makes lift values comparable across attributes and across blocks with different voter counts.
- **Multiple metrics at different abstraction levels catch different problems.** Lift detects direction and magnitude. Odds ratio detects association strength even for rare events. Wilson CI quantifies uncertainty. Chi-squared contribution (for clusters) identifies which cells drive the overall non-uniformity. No single metric covers all needs.
- **Detection thresholds are empirical, not theoretical.** The 2.0/1.3/1.1 thresholds were calibrated against the test config. Different preference weights, voter counts, or batch sizes would need different thresholds. The thresholds are in code, not config, because changing them requires re-validating the acceptance tests.
- **Vote-level rates, not image-level rates.** An image shown 10 times and selected 8 has a vote-level rate of 0.80. If instead we counted "was selected at least once" (image-level), we'd lose granularity — a universally popular image and a sometimes-selected image would both score 1.0. Vote-level rates preserve the signal.
- **Average lift across target attributes smooths single-attribute noise.** A block targeting Earth+Moon might have lift 3.2 for Earth but only 1.8 for Moon (because Moon appears in more images overall). Averaging gives 2.5, which correctly classifies as "detected." Using min or max would be brittle.

## Applicability

Lift-based analysis applies to any system comparing behavior rates between subgroups:
- Marketing: campaign response lift over baseline
- Recommendation systems: click-through rate lift for a treatment group
- Content moderation: flagging rate lift for specific content categories

Does NOT apply when:
- The base rate is near zero (lift becomes numerically unstable — use odds ratio instead)
- The question is causal rather than observational (lift shows association, not causation)
- Costs are asymmetric (a rare-but-expensive event needs cost-weighted metrics, not lift)

## Related Lessons

- [Lesson 028: Chi-Squared for Bias Detection](../block4/028_chi_squared_for_bias_detection.md) — chi-squared tests the existence of bias; lift quantifies its magnitude
- [Lesson 041: Utility Function for Synthetic Voting Bias](041_utility_function_for_synthetic_voting_bias.md) — the utility function plants bias at a known strength; lift measures how much of that signal survives through the pipeline
- [Lesson 030: Reliability Delta as Noise Measurement](../block4/030_reliability_delta_as_noise_measurement.md) — reliability delta measures noise from biased voters; lift measures their observable effect on attribute selection
