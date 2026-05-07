# Lesson 016: Krippendorff's Alpha for Sparse Agreement

## Problem

We want to measure whether voters agree on which images are good. With 100 voters and 12,217 images, the voter-image matrix is >98% missing — most voters never saw most images. Standard agreement metrics require complete matrices. We need a reliability measure that handles extreme sparsity.

## Why It Matters

Inter-rater reliability tells us whether voter preferences reflect genuine consensus or random noise. Low agreement suggests the vote data is too sparse or too noisy to drive calendar selection with confidence. High agreement means the preference scores are trustworthy. Without a reliability metric, we can't assess the quality of our inputs.

## Design Choice: Krippendorff's Alpha via Coincidence Matrix

### Key terms

- **Inter-rater reliability**: A family of statistics measuring the extent to which different raters (voters) give the same ratings to the same items (images). Perfect agreement = 1.0, chance agreement = 0.0, systematic disagreement < 0.0.

- **Krippendorff's alpha**: A general-purpose reliability measure developed by Klaus Krippendorff. Its key advantage: it handles **any number of raters**, **any number of categories**, **any measurement level** (nominal, ordinal, interval, ratio), and — critically — **missing data**. Most other reliability metrics require complete matrices.

- **Coincidence matrix**: The core of Krippendorff's alpha computation. Instead of working with the raw rater-item matrix, we build a matrix of how often pairs of values co-occur across items. For each item rated by m raters, we count all m*(m-1) ordered pairs of assigned values, weighted by 1/(m-1). This naturally handles variable numbers of raters per item — items with more raters contribute more to the coincidence matrix, but each individual pair is weighted appropriately.

- **Agreement vs. chance agreement**: Alpha = 1 - (observed_disagreement / expected_disagreement). Observed disagreement comes from the coincidence matrix diagonal vs. off-diagonal. Expected disagreement is what we'd see if raters assigned values randomly with the same marginal frequencies. Alpha corrects for chance agreement — unlike raw percentage agreement, it won't be inflated by unbalanced base rates.

- **Fleiss' kappa (and why it fails here)**: Fleiss' kappa extends Cohen's kappa to multiple raters, but it requires **every rater to rate every item**. With our 100x12,217 matrix at <2% density, Fleiss' kappa is mathematically undefined. We store NULL for this metric.

- **Kendall's W**: Measures concordance among rankings. Requires **complete rankings** — every rater must rank every item. Even more restrictive than Fleiss' kappa. Also stored as NULL.

### Implementation: coincidence matrix formulation

The implementation is about 50 lines of numpy:

1. For each item (column in the matrix), collect the non-NaN ratings
2. If fewer than 2 raters rated this item, skip it (can't measure agreement with <2 raters)
3. For each pair of raters who both rated the item, add their value pair to the coincidence matrix, weighted by 1/(m-1) where m is the number of raters for that item
4. Compute marginal frequencies from the coincidence matrix
5. Observed disagreement: 1 - trace(coincidence) / total
6. Expected disagreement: 1 - sum(n_k * (n_k - 1)) / (n * (n - 1)) where n_k are marginal frequencies

### Nominal vs. ordinal variants

We compute nominal alpha for batch voting (binary: selected=1, not selected=0) and ordinal alpha for category ranking (Borda scores: 3, 2, 1). The ordinal variant uses a different distance metric that accounts for the ordering of categories — disagreeing by 2 ranks is worse than disagreeing by 1.

## Alternatives Considered

1. **Fleiss' kappa**: Cannot handle missing data. Undefined for our matrix.
2. **Scott's pi / Cohen's kappa**: Designed for 2 raters only.
3. **Intraclass correlation (ICC)**: For continuous ratings. Batch voting is binary, so ICC doesn't apply directly.
4. **Pairwise Spearman correlations**: Compute Spearman rank correlation for each pair of voters who both rated at least N common items, then average. Implementable but unreliable — most voter pairs share very few items, making individual correlations extremely noisy.
5. **External library (krippendorff package)**: Available on PyPI but adds a dependency for ~50 lines of numpy. We implemented from scratch to avoid the dependency.

## What Was Learned

Krippendorff's alpha is the only standard reliability metric that works out of the box with extremely sparse data. The coincidence matrix formulation is elegant — it naturally weights items by how many raters evaluated them, without requiring any special handling of missing values. The expected result for synthetic data is low alpha (voters are noisy by design, especially the 10% "random" profile), which is exactly what we observe. When real vote data arrives, alpha will likely be higher because real voters have more consistent preferences than synthetic ones.

The main caveat: alpha is sensitive to base rate. With batch voting where the base rate is 10% (5 selected out of 50 shown), even random raters will often agree on "not selected" — this inflates raw agreement but alpha corrects for it. If alpha is still near zero after correction, voter agreement is genuinely weak.
