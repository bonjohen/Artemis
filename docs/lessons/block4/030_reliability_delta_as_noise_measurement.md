# Lesson 030: Reliability Delta as Noise Measurement

## Problem

We know that 20% of synthetic voters are intentionally noisy (10% position-biased, 10% random). We compute Krippendorff's alpha on all voters and get a moderate value (~0.52). But how much of the low agreement is caused by these noisy voters vs. genuine preference diversity among neutral voters? We need to isolate the noise contribution.

## Why It Matters

Agreement metrics on a mixed population conflate two things: genuine preference diversity (some people like dramatic images, others like crew photos) and noise (random voters and position-biased voters who aren't responding to image quality at all). If you remove the noise and alpha barely changes, the low agreement reflects real diversity — which is fine. If removing the noise dramatically increases alpha, the noise is masking consensus — which means the preference scores are less reliable than they appear.

## What Happened

1. Computed Krippendorff's alpha on all 100 synthetic voters' batch ballot data. Got a moderate alpha reflecting the mix of signal and noise.
2. Recomputed alpha on the same data but excluding voters with `synthetic_profile_code IN ('position_biased', 'random')`. This removes 20% of voters.
3. Compared the two: `alpha_delta = alpha_clean - alpha_all`. A positive delta means the excluded voters were lowering agreement (injecting noise). The magnitude tells you how much.
4. Reused the existing `krippendorff_alpha_nominal` function from `models/reliability.py` for both computations. No new algorithm — just a different filter on the input matrix.
5. The key design decision was *which voters to exclude*. We exclude by profile code (available in `dim_voter.synthetic_profile_code`) rather than by behavior detection, because this is validation — we're checking whether the system can distinguish signal from noise, so we use the ground truth labels.
6. In a real-data scenario (no profile codes), the same technique applies but the exclusion set comes from behavioral detection: voters flagged by the position-bias test or low-agreement scores. The validation step here proves the concept; the production step would close the loop.

## Design Choice: Delta Over Absolute

### Why report the delta, not just the clean alpha?

Alpha alone is hard to interpret — is 0.52 good or bad? The answer depends on the domain. But a delta of +0.08 (from 0.52 to 0.60) is interpretable: 15% of the disagreement was caused by noisy voters. This is actionable — you can decide whether 15% noise is acceptable or whether you need to weight-down suspected noisy voters in the preference scoring.

### Why not build noise detection into the scoring pipeline?

The validation module detects noise and reports it. The scoring pipeline could incorporate noise-adjusted weights (downweight suspected noisy voters). We deliberately kept these separate: validation proves the noise exists and measures its impact; the scoring pipeline is where you'd act on it. Mixing detection and correction in one step makes it impossible to know whether the correction helped.

## Key Insights

- **Agreement deltas isolate noise from diversity.** A single alpha number conflates signal heterogeneity with noise. The delta between "all voters" and "clean voters" separates them. This is more useful than either number alone.
- **Reuse existing metrics with different filters.** No new algorithm was needed — just a SQL WHERE clause change. The infrastructure for computing alpha on arbitrary voter subsets was already built (the coincidence matrix handles variable-size inputs). This is a common pattern: the metric stays the same, the population changes.
- **Validation uses ground truth; production uses detection.** In validation, we know which voters are noisy (synthetic profile codes). In production, we'd identify them through behavioral signals (position-bias test, low consistency). The validation step proves that removing noisy voters improves agreement; the production step applies the same logic to detected (not labeled) voters.
- **Small deltas are informative too.** If removing 20% of voters (the noisy ones) barely changes alpha, it means the remaining 80% already disagree substantially. This tells you that preference diversity is real, not noise-induced — which affects how aggressively the optimizer should pursue consensus vs. diversity.
- **Profile-level analysis complements the delta.** Beyond the binary "all vs. clean" comparison, reporting per-profile agreement (mean Jaccard with population top) shows *how* different profiles deviate. Random voters have low agreement with everyone; position-biased voters have moderate agreement (they still respond to quality, just with a positional overlay); visual-drama voters agree with the consensus on dramatic images but diverge on others.

## Applicability

This pattern applies to any system measuring agreement in a heterogeneous population:
- Survey reliability with suspected satisficers or inattentive respondents
- Crowdsourcing quality assessment (remove flagged workers, measure alpha delta)
- Sensor fusion with suspected faulty sensors (remove suspected bad sensors, measure consensus change)

Does NOT apply when:
- All raters are equally trusted (no subpopulation to exclude)
- The metric isn't decomposable by subpopulation (some metrics require all raters)
- The goal is prediction, not agreement measurement

## Related Lessons

- [Lesson 016: Krippendorff's Alpha for Sparse Agreement](../block2/016_krippendorffs_alpha_for_sparse_agreement.md) — the foundation metric reused here with filtered populations
- [Lesson 028: Chi-Squared for Bias Detection](028_chi_squared_for_bias_detection.md) — detects the biases whose impact on reliability this lesson measures
- [Lesson 017: Composite Scoring with Heterogeneous Signals](../block2/017_composite_scoring_with_heterogeneous_signals.md) — the scoring pipeline whose reliability we're validating
- [Lesson 042: Lift as the Primary Bias Detection Metric](../block6/042_lift_as_primary_bias_metric.md) — reliability delta measures noise from biased voters; lift measures their observable effect on attribute selection
