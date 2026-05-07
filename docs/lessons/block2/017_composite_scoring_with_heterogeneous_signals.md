# Lesson 017: Composite Scoring with Heterogeneous Signals

## Problem

We have three different types of preference data — batch selection rates, Elo ratings from pairwise comparisons, and Borda scores from category rankings. Each covers a different subset of images, uses a different scale, and captures a different aspect of preference. Most images have data from only one type (batch). We need a single composite score per image that the calendar optimizer can use.

## Why It Matters

The calendar optimizer needs to compare any image against any other image on a single preference dimension. Three separate scores, each on a different scale and each covering a different subset, don't work — you can't compare an Elo score of 1532 to a selection rate of 0.15. The composite score must: (a) work for all 12,217 images, (b) incorporate secondary signals where available, and (c) not break when signals are missing.

## What Happened

<!-- reconstructed from git history (876828a) and lesson context -->

1. Had three separate preference signals on different scales: batch selection rates as Beta posteriors (0.15–0.38 range, all 12,217 images), Elo ratings (1300–1700 range, ~394 images), and Borda scores (1–30 range, ~75 images). The calendar optimizer needed a single comparable score per image.
2. Considered a simple weighted average but rejected it — what's the "normalized Elo" for an image with no pairwise data? Zero would actively penalize it. Mean-imputation would claim false knowledge.
3. Chose quantile normalization to make scales comparable: rank each signal's values to [0, 1]. This eliminates the Elo-is-1500 vs. Borda-is-6 problem without requiring arbitrary scale factors.
4. Designed a multiplicative adjustment formula: `adjusted_mean = posterior_mean × (1 + 0.15 × elo_quantile + 0.10 × borda_quantile)`. Multiplicative preserves ordinal ranking unless secondary signals are strong enough to override. Maximum total adjustment is 25%.
5. Set weights conservatively: batch at ~85% (most complete coverage), Elo at 15% (most informative per observation but sparse), Borda at 10% (least reliable due to exposure-set problem). The backbone dominates by design — batch data covers all images, secondary signals cover 3-6%.
6. Added two derived metrics for downstream use: polarization (voter disagreement, computed as std dev of per-voter binary outcomes) and broad appeal (posterior_mean × (1 - polarization_quantile)). These capture dimensions that raw preference doesn't — an image with high posterior_mean but high polarization divides voters and may be a risky calendar choice.

## Design Choice: Beta Posterior Backbone with Quantile-Rank Adjustments

### Key terms

- **Quantile normalization**: Converting raw scores to their rank position within the distribution, scaled to [0, 1]. The highest-scoring image gets 1.0, the lowest gets 0.0, and everything else is linearly interpolated by rank. This eliminates scale differences — Elo ratings (range ~1300-1700) and Borda scores (range 1-30) become directly comparable.

- **Multiplicative adjustment**: The formula `adjusted_mean = posterior_mean * (1 + 0.15 * elo_quantile + 0.10 * borda_quantile)`. The adjustment is multiplicative, not additive, which means:
  - An image with posterior_mean=0.30 and top-ranked Elo gets: 0.30 * 1.15 = 0.345 (a 15% boost)
  - An image with posterior_mean=0.10 and top-ranked Elo gets: 0.10 * 1.15 = 0.115 (same 15% boost, smaller absolute change)
  - Multiplicative adjustments preserve the prior's ordinal ranking unless the secondary signals are strong enough to override

- **Heterogeneous data fusion**: The general problem of combining measurements from different instruments, scales, or populations into a single estimate. The key challenge is **commensurability** — making values comparable across different measurement types. Quantile normalization is a simple solution; more sophisticated approaches include z-score normalization, copula methods, or latent factor models.

- **Missing-signal graceful degradation**: When an image has no Elo score, its Elo adjustment is 0 (no boost, no penalty). When an image has no Borda score, same. The Beta posterior is the fallback for every image. Images with data from all three types get the most informed estimate; images with only batch data get a reasonable estimate; images with no data at all get a pure prior with wide uncertainty bounds.

- **Polarization vs. broad appeal**: Two derived metrics:
  - **Polarization** = standard deviation of per-voter binary outcomes. An image selected by 5 of 10 viewers (50% rate, polarizing) vs. an image selected by 1 of 10 viewers (10% rate, low appeal) — both might have similar posterior means with enough smoothing, but they feel very different as calendar choices.
  - **Broad appeal** = posterior_mean * (1 - polarization_quantile). Penalizes images that divide voters. A calendar should feature images with broad consensus, not images that are loved by some and ignored by others.

### Weight choices: 0.15 Elo, 0.10 Borda

These are deliberately conservative. The rationale:

1. **Batch data is the most complete.** All 12,217 vote-pool images appear in batch ballots. Batch should dominate the composite.
2. **Elo is the most informative per observation.** A pairwise comparison directly reveals relative preference. But with only 2,000 comparisons, coverage is too sparse to justify a large weight.
3. **Borda is the least reliable.** The exposure-set problem (lesson 015) means Borda scores may be systematically biased — images shown more often in rankings accumulate more points regardless of quality.
4. **The adjustments are capped.** Maximum total adjustment is 25% (0.15 + 0.10), which can nudge rankings but not dramatically flip them.

### What happens for images with no batch data

This shouldn't happen with the current vote structure (all 12,217 images are in the batch pool), but the design handles it: such images receive the pure Beta(2,8) prior (mean 0.20, wide credible interval). They'll score in the middle of the pack by default and can only move based on Elo/Borda signals.

## Alternatives Considered

1. **Simple weighted average**: `0.5 * selection_rate + 0.3 * elo_normalized + 0.2 * borda_normalized`. Simpler but doesn't handle missing values gracefully — what's the "normalized Elo" for an image with no pairwise data? Zero? That actively penalizes it.

2. **Bayesian hierarchical model**: A proper joint model that treats all three vote types as observations of a latent preference parameter. Theoretically ideal but requires MCMC or variational inference, adds significant complexity, and the synthetic data doesn't justify the investment.

3. **Separate scores, no composite**: Let the optimizer use all three scores independently as separate objectives. Increases the optimization problem's dimensionality and forces the optimizer to make the trade-offs that the composite score already resolves.

4. **Rank aggregation (Borda on the score rankings)**: Rank images by each method independently, then aggregate ranks. Loses magnitude information — an image ranked #1 by a huge margin looks the same as one ranked #1 by a hair.

## What Was Learned

The key insight is that **the backbone matters more than the adjustments**. The Beta posterior from batch data determines 75-100% of each image's composite score. Elo and Borda are nudges, not drivers. This is the right design for our data density — batch data is dense, the other signals are sparse. As real vote data arrives and pairwise/category coverage grows, the adjustment weights can be increased.

The quantile-rank approach to normalization is simple and robust but has a weakness: it's sensitive to the population of images that have a given score type. If only 50 images have Elo scores, the quantile ranks are very coarse (each rank step is 2%). With 500+ images, the granularity is fine enough for the multiplicative adjustment to be meaningful.
