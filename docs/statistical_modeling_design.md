# Statistical Modeling Design Document

## 1. Purpose

Phase 3 produces image-level preference scores from vote data. These scores are the primary input to Phase 4's calendar optimization, which selects 13 images that balance voter preference, visual diversity, mission coverage, and month suitability. Without defensible preference scores, the optimizer has nothing to optimize against.

## 2. Scope

This design covers four scoring components, a composite scoring method, inter-rater reliability measurement, and mart table population. It does not cover month suitability, cover suitability, or calendar optimization (those are Phase 4).

## 3. Core Design Principles

The scoring system must handle three characteristics of the Artemis vote data:

1. **Extreme sparsity.** With 500 batch ballots across 12,217 images, most images are shown only 1-2 times. Raw selection rates are meaningless at this exposure level. Every score must be smoothed or bounded.

2. **Heterogeneous vote types.** Batch ballots, pairwise comparisons, and category rankings each measure preference differently. Most images appear in only one vote type. The composite score must gracefully degrade when signals are missing.

3. **Synthetic data for now.** The current data is from 100 synthetic voters with known profiles (60% neutral, 20% visual-drama, 10% position-biased, 10% random). Scores should be validated against the synthetic ground truth but not overfit to it.

## 4. Primary User Stories

1. As a calendar optimizer, I need a single preference score per image so I can balance appeal against diversity.
2. As a reviewer, I need uncertainty bounds so I can tell whether a high-scoring image is genuinely preferred or just lucky with sparse data.
3. As a bias analyst, I need inter-rater reliability metrics to assess whether voter agreement is real or driven by synthetic profile homogeneity.

## 5. Functional Requirements

### 5.1 Batch Voting Scores

The batch voting mode shows 50 random images and asks voters to select 5 favorites. This produces binary outcomes (selected / not selected) with known exposure.

**Selection rate** is the raw proportion: selected_count / shown_count. Unreliable at low exposure.

**Wilson lower bound** is a frequentist confidence interval lower bound for a binomial proportion. It answers: "Given this sample, what is the worst-case selection rate at 95% confidence?" Wilson is preferred over the raw Wald interval because it performs correctly at extreme proportions (0% or 100%) and low sample sizes.

**Beta-Binomial posterior** is the Bayesian approach. The Beta distribution is the conjugate prior for binomial data, meaning the posterior is also a Beta distribution with a closed-form solution:
- Prior: Beta(alpha=2, beta=8), encoding a ~20% expected selection rate
- Posterior: Beta(alpha + selected, beta + (shown - selected))
- Posterior mean: (alpha + selected) / (alpha + beta + shown)

The prior choice of Beta(2, 8) is slightly generous relative to the 10% base rate (5 of 50) because the vote pool contains many non-photogenic frames, so images that make it into ballots are already somewhat pre-filtered.

### 5.2 Pairwise (Elo) Scores

The pairwise mode shows two images side by side and asks which is better. The Elo rating system translates these binary outcomes into a continuous strength score.

**Standard Elo** with K-factor 32 and starting rating 1500. For each comparison:
- Expected score: E_w = 1 / (1 + 10^((R_loser - R_winner) / 400))
- Rating update: R_new = R_old + K * (actual - expected)

K=32 is a moderate learning rate — responsive enough to converge with sparse data, not so aggressive that a single upset destroys a rating.

**Bradley-Terry-Luce (BTL)** is deferred. BTL estimates a strength parameter for each item by maximum likelihood on the comparison graph. It requires a connected comparison graph (every item reachable from every other through chains of comparisons). With 2,000 pairwise votes across 12,217 images, the graph is overwhelmingly disconnected — most images appear in zero or one pair. BTL would either fail to converge or produce meaningless estimates for isolated nodes. The `btl_score` column remains NULL until pairwise data reaches sufficient density (~20K+ comparisons).

### 5.3 Category (Borda) Scores

The category mode asks voters to rank their top 3 images within a category. Ranks are converted to Borda scores: rank 1 = 3 points, rank 2 = 2 points, rank 3 = 1 point.

Scores are aggregated per image across all category ranking submissions. Only images that appear in category rankings receive Borda scores; the rest are NULL.

### 5.4 Composite Score

The composite score uses the Beta posterior as its backbone and adjusts for secondary signals:

1. Compute the Beta posterior mean from batch data (or pure prior for unshown images)
2. Convert Elo scores to quantile ranks in [0, 1]
3. Convert Borda scores to quantile ranks in [0, 1]
4. Apply multiplicative adjustment: adjusted_mean = posterior_mean * (1 + 0.15 * elo_quantile + 0.10 * borda_quantile)

This design ensures:
- Images with only batch data get pure posterior scores
- Images with additional Elo/Borda data get a modest boost proportional to their relative standing
- The adjustment is multiplicative, not additive, so it preserves the posterior's scale
- The weights (0.15 Elo, 0.10 Borda) are conservative — secondary signals nudge, not dominate

### 5.5 Uncertainty and Appeal Metrics

**Uncertainty score:** Width of the 95% credible interval (posterior_upper - posterior_lower). Wide intervals mean the image needs more data.

**Polarization score:** Standard deviation of per-voter binary outcomes for each image. An image that half of voters love and half ignore is more polarizing than one that most voters feel lukewarm about.

**Broad appeal score:** posterior_mean * (1 - polarization_quantile). This penalizes polarizing images. A calendar benefits from images with broad appeal rather than niche favorites.

### 5.6 Inter-Rater Reliability

**Krippendorff's alpha** is the only metric computed. It is designed for incomplete data matrices and handles the >98% missingness in the batch voting matrix. The implementation uses the coincidence matrix formulation, which counts how often raters who both rated the same item agreed, weighted by the number of raters per item.

**Fleiss' kappa** and **Kendall's W** require complete matrices (every rater rates every item). They are stored as NULL.

## 6. Module Structure

```
src/artemis_calendar/models/
    __init__.py          # compute_preference_scores() orchestrator
    batch_scores.py      # Selection rate, Wilson lower bound, Beta posterior
    pairwise_scores.py   # Elo computation
    category_scores.py   # Borda aggregation
    composite.py         # Score merging, uncertainty, polarization, broad appeal
    reliability.py       # Krippendorff's alpha (nominal and ordinal)
    marts.py             # Write to mart_image_preference_score, backfill cluster marts
```

Entry point: `compute_preference_scores(conn) -> dict[str, int]`

Each sub-module returns a dict keyed by image_sk. The orchestrator merges them and writes to the mart table in a single transaction.

## 7. Data Flow

```
fact_batch_ballot_image  -->  batch_scores.py   -->  {image_sk: {selection_rate, wilson, posterior}}
fact_pairwise_vote       -->  pairwise_scores.py -->  {image_sk: {elo_score, wins, losses}}
fact_category_ranking_image -> category_scores.py -> {image_sk: {borda_score, count, mean}}
                                    |
                                    v
                              composite.py  -->  {image_sk: {all columns}}
                                    |
                                    v
                              marts.py  -->  mart_image_preference_score (INSERT)
                                        -->  mart_cluster_top_images (UPDATE backfill)
                                        -->  mart_image_cluster_summary (UPDATE backfill)
```

## 8. Output Tables

### mart_image_preference_score
One row per image per scoring run. 17 score columns covering raw counts, method-specific scores, Bayesian posterior, uncertainty, and appeal.

### mart_inter_rater_reliability
One row per vote mode per reliability run. Krippendorff's alpha populated; other metrics NULL pending sufficient data.
