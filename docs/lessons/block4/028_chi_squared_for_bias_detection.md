# Lesson 028: Chi-Squared Tests for Bias Detection at Small Scale

## Problem

We planted known biases in synthetic vote data — 10% of voters had position bias (preferring earlier-displayed images), 20% had visual-drama bias (preferring dramatic images). We need statistical tests that can detect these biases with only 100 voters and 500 ballots, without requiring heavy statistical machinery.

## Why It Matters

Bias detection in voting data determines whether preference scores are trustworthy. If position bias inflates certain images' scores, the calendar optimizer will select images that happened to be shown first, not genuinely popular ones. The challenge is that detection must work at the scale of the available data — sophisticated methods that require thousands of voters are useless when you have 100. Choosing the right test avoids both false confidence ("no bias detected" when bias exists) and false alarms.

## What Happened

1. Needed to detect two types of planted bias: display-position bias in batch ballots (do earlier-displayed images get selected more?) and cluster concentration (are certain visual clusters over-represented in selections?).
2. Considered logistic regression of `was_selected ~ display_position` for position bias. While theoretically sound, logistic regression on 500 binary outcomes with a weak effect (only 10% of voters are biased) risks low power. Also adds a statsmodels dependency.
3. Chose chi-squared test of independence instead. Split 50 display positions into thirds (0-16, 17-33, 34-49), built a 3×2 contingency table (position group × selected/not-selected), ran `scipy.stats.chi2_contingency`. Simpler, no extra dependencies (scipy already required for optimization), and the contingency table is immediately interpretable.
4. For cluster bias, used chi-squared goodness-of-fit (`scipy.stats.chisquare`). Expected counts proportional to cluster size; observed counts from actual selections. Filtered clusters with expected < 1.0 to avoid chi-squared instability with small expected values.
5. Supplemented with a binomial test for pairwise left/right bias (`scipy.stats.binomtest` against H₀: p=0.5). This is the most straightforward test in the toolkit — one proportion, one null hypothesis.
6. Position bias was detectable at p < 0.05 even with only 500 ballots, because the 10% position-biased voters with strength 0.4 create enough signal in aggregate. The effect size (early selection rate minus late selection rate) was small but consistent.
7. Computed lift ratios per cluster (observed/expected) as a complement to the chi-squared p-value. The p-value says "is the distribution non-uniform?" but the lift ratio says "which clusters are over-selected and by how much?" — the actionable part.

## Design Choice: Distribution Tests Over Regression

### Why chi-squared over logistic regression

Chi-squared tests ask "is the distribution of selections independent of position?" — which is exactly the bias question. Logistic regression would estimate the coefficient and confidence interval, which is more informative in theory but:

- Adds a dependency (statsmodels or manual implementation)
- Requires more data for stable coefficient estimates with a weak effect
- The coefficient's magnitude matters less than its presence — we want a binary answer ("is there bias?") more than a precise effect size
- The contingency table is immediately auditable: you can look at three numbers (selection rates per third) and see the bias

### Why goodness-of-fit for clusters

Cluster bias isn't about a single predictor — it's about whether selections are distributed proportionally across 25 clusters. Goodness-of-fit is the natural test: "does the observed distribution match the expected one?" The alternative (25 individual proportion tests with Bonferroni correction) is both less powerful and harder to interpret.

### The expected < 1.0 filter

Chi-squared approximations break down when expected cell counts are small. The standard rule is expected ≥ 5, but with 25 clusters of varying sizes and limited selections, strict application would eliminate too many clusters. We used expected ≥ 1.0 as a pragmatic threshold — permissive enough to keep most clusters in the test, conservative enough to avoid cells where a single observation dominates.

## Key Insights

- **Match the test to the question, not the sophistication.** Chi-squared and binomial tests are textbook methods, but they answer exactly the right questions for bias detection. More complex methods (mixed-effects models, Bradley-Terry decomposition) would answer questions we weren't asking at this scale.
- **Lift ratios complement p-values.** The chi-squared test says "the distribution is non-uniform" (p < 0.05), but doesn't say which clusters are the problem or by how much. Lift ratios (observed/expected per cluster) are the actionable output — they tell the optimizer which clusters to penalize.
- **Small-scale bias detection is about aggregation, not individual detection.** With 10% biased voters, no single ballot reveals bias. But 500 ballots × 50 images × position information = 25,000 position observations, which is ample for a chi-squared test. The test detects the population-level pattern, not individual biased voters.
- **Filter expected cell counts to avoid false positives.** Clusters with expected < 1 selection would trigger chi-squared significance from a single selection. Filtering these out prevents the test from flagging rare clusters that happened to have one image selected.
- **Binomial tests are the cleanest tool for proportion questions.** "Is the left-image win rate 50%?" is a textbook binomial hypothesis test. No contingency table, no regression, no assumptions about linearity. The simpler the question, the simpler the test.

## Applicability

This approach works for any system that needs to detect distributional bias in preference data:
- A/B test position effects in recommendation systems
- Detecting popularity bias in collaborative filtering
- Auditing fairness in ranked outputs (are certain categories over-represented?)

Does NOT apply when:
- You need to estimate effect size precisely (use regression)
- The bias is continuous, not categorical (use correlation or regression)
- You have enough data for mixed-effects models that can account for voter-level random effects

## Related Lessons

- [Lesson 016: Krippendorff's Alpha for Sparse Agreement](../block2/016_krippendorffs_alpha_for_sparse_agreement.md) — another statistical method chosen specifically for the data's structure (sparsity there, small scale here)
- [Lesson 025: Multiple Methods as Baselines](../block3/025_multiple_selection_methods_as_baselines.md) — bias detection validates the inputs; multiple methods validate the outputs
- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — bias detection only works because the synthetic generator plants known biases with ground truth
- [Lesson 041: Utility Function for Synthetic Voting Bias](../block6/041_utility_function_for_synthetic_voting_bias.md) — the utility function that plants attribute-based bias detected by chi-squared tests
- [Lesson 042: Lift as the Primary Bias Detection Metric](../block6/042_lift_as_primary_bias_metric.md) — lift quantifies bias magnitude where chi-squared detects its existence
