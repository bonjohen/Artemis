# Lesson 015: Borda Count for Ranked Voting

## Problem

The Artemis category voting mode asks voters to rank their top 3 images within a category. We need to convert these partial rankings into numeric scores that can be aggregated across voters and combined with batch and pairwise preference signals.

## Why It Matters

Ranked voting captures more information than binary choice — a voter who ranks image A first, B second, and C third is telling us more than a voter who just picks A. The scoring method determines whether this extra information is preserved or lost.

## Design Choice: Standard Borda Count with 3/2/1 Scoring

### Key terms

- **Borda count**: A positional voting system where each rank position receives a fixed number of points. In our case: rank 1 = 3 points, rank 2 = 2 points, rank 3 = 1 point. Points are summed across all voters who ranked the image. Named after Jean-Charles de Borda (1733-1799), who proposed it for French Academy elections.

- **Positional voting**: Any voting system where the score depends on the rank position, not on which specific alternatives were ranked above or below. Borda is the simplest and most common positional system.

- **Rank-to-score conversion**: The mapping from ordinal positions (1st, 2nd, 3rd) to cardinal scores (3, 2, 1). Alternative conversions include: linear (3, 2, 1), geometric (4, 2, 1), or equal weighting (1, 1, 1 — equivalent to just counting appearances). We use linear because it's the standard and the differences between alternatives are small with only 3 ranks.

- **Plackett-Luce alternative**: A probabilistic model for ranked data, analogous to Bradley-Terry-Luce for pairwise data. It assumes each item has a strength parameter and the probability of a ranking is proportional to the product of conditional probabilities at each rank. More principled than Borda but requires more data and has the same connectivity issues as BTL. Deferred for the same reasons.

- **Exposure-set problem**: The critical limitation of Borda scoring in our context. When a voter ranks their top 3 in a category, we know which images they ranked — but we don't know which images they saw and rejected. If the category contains 100 images, an image that wasn't ranked could mean "wasn't shown" (missing data) or "was shown and beaten by 3 others" (negative signal). Without the exposure set, we can't distinguish these cases. We treat unranked images as missing, which may slightly overestimate scores for images that were seen but not ranked.

### Aggregation approach

For each image, we sum the Borda scores across all ranking submissions where it appeared:
- `borda_score`: Total points (sum of 3/2/1 across all rankings)
- `borda_count`: Number of times ranked (appears in any position)
- `borda_mean`: Average score per ranking appearance (borda_score / borda_count)

The `borda_score` (total) is used in the composite because it rewards images that are both highly ranked and frequently ranked. An image ranked #1 in 10 submissions (30 points) is stronger than one ranked #1 in 2 submissions (6 points), even though both have the same mean.

## Alternatives Considered

1. **Average rank**: Use mean rank position instead of Borda points. Loses the distinction between "ranked once as #1" and "ranked ten times as #1."
2. **Plackett-Luce model**: Full probabilistic model for ranked data. Deferred — same connectivity and sparsity issues as BTL.
3. **Category-specific models**: Fit separate preference models within each category. Would produce more precise within-category rankings but doesn't help with cross-category comparison.
4. **Dowdall system (harmonic)**: Scores of 1, 1/2, 1/3 for ranks 1, 2, 3. Gives even more weight to first place. Considered unnecessary with only 3 ranks.

## What Was Learned

Borda count is the right simple default for partial ranking data. Its main advantage is transparency — it's easy to explain that "rank 1 = 3 points, rank 2 = 2 points, rank 3 = 1 point" and the aggregation is just a sum. The exposure-set problem is the biggest limitation and there's no clean fix without logging which images each voter actually saw. For the composite score, Borda's contribution is modest (10% weight via quantile rank) precisely because of this uncertainty.
