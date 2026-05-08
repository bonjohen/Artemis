# Lesson 029: Ground-Truth Recovery as Optimizer Validation

## Problem

We have a calendar optimizer that selects 13 images from 12,217 using a weighted objective function (popularity, diversity, month-fit, cover-fit, redundancy penalty). The optimizer reports an objective score, but a high score doesn't prove the optimizer is selecting the *right* images — it could be optimizing a broken objective. We need an external measure of optimizer quality.

## Why It Matters

Optimizers optimize what you tell them to. If the objective function is miscalibrated (wrong weights, missing a constraint, or over-indexing on one signal), the optimizer will faithfully maximize the wrong thing and report a high score while doing it. Self-reported objective scores are circular validation. Ground-truth recovery — "did the optimizer find the images we know are good?" — breaks the circularity by measuring against an independent standard.

## What Happened

1. The synthetic data generator assigns each of 12,217 images a `ground_truth_calendar_role`: "cover", "month", or "distractor". Images with latent_general_appeal > 0.90 and latent_cover_value > 0.70 are marked "cover"; those with appeal > 0.85 are "month"; the rest are "distractor". This creates a known ground-truth calendar slate.
2. After running the optimizer to produce 5 candidate calendars (methods A–E), we compared each method's 13-image slate against the ground-truth set. The metric: what fraction of ground-truth "month" and "cover" images appear in the candidate's slate?
3. Recovery rate varies by method. Method A (naive top-13) and Method B (cluster-limited) recover different subsets. This is expected — the methods make different tradeoffs between popularity and diversity.
4. Also checked whether each method's designated cover image has `ground_truth_calendar_role = 'cover'`. This tests whether the cover-scoring function aligns with the planted cover suitability.
5. Combined recovery metrics with slate diversity (distinct clusters, max CLIP cosine similarity) to produce a per-method comparison table. This lets us see whether methods that sacrifice recovery gain diversity, and whether the tradeoff is worth it.
6. Stored results in `mart_calendar_validation` for reproducibility. Each validation run gets its own ID, so results from different optimization runs or scoring parameters can be compared.

## Design Choice: Recovery Rate + Diversity, Not Just Recovery

### Why not just maximize recovery?

100% ground-truth recovery would mean the optimizer is a perfect oracle — but that's not actually desirable. The ground truth is assigned by a hash-based heuristic, not by genuine aesthetic judgment. A method that recovers 10/13 ground-truth images but adds 3 images from underrepresented clusters may produce a better calendar than one that recovers 13/13 but has redundant selections.

Recovery rate measures alignment with planted quality signals. Diversity metrics (cluster count, max pairwise similarity) measure whether the optimizer adds value beyond raw popularity ranking. The combination tells the full story.

### Why compare all methods, not just the winner?

The purpose of validation is to understand the optimizer's behavior, not to crown a winner. If Method A (naive top-13) recovers 8/13 and Method E (MMR greedy) recovers 5/13 but has 0 CLIP overlap, that tells us exactly how much diversity costs in terms of ground-truth alignment. This is the information needed to calibrate the objective function weights.

## Key Insights

- **Self-reported scores are circular.** An optimizer's objective score measures how well it optimized *its own* objective. Ground-truth recovery measures how well it solved *the actual problem*. These are different questions, and both answers are needed.
- **Recovery rate is a necessary but not sufficient metric.** High recovery confirms the optimizer finds good images. Low recovery could mean the optimizer prioritizes diversity over raw quality (which may be correct for a calendar) or that the scoring pipeline is broken (which is a bug). Pairing recovery with diversity metrics disambiguates.
- **Synthetic ground truth is cheap validation infrastructure.** Because the ground truth is assigned by deterministic rules on planted latent scores, it's perfectly reproducible and costs nothing to compute. Real ground truth (human expert curation) is expensive and subjective. Synthetic ground truth is a lower bound — if the optimizer can't find synthetically good images, it won't find really good ones either.
- **Store validation results, not just log them.** Persisting recovery and diversity metrics in a mart table enables comparison across optimization runs. If you change the objective weights and re-run, you can see whether recovery improved without re-running validation manually.
- **Cover image validation needs its own test.** The cover image has different criteria than monthly images (simpler composition, typography space, broad symbolism). Testing cover recovery separately from month recovery ensures the cover-scoring function is working, not just the general preference scoring.

## Applicability

This pattern applies to any multi-objective selection system:
- Recommendation system evaluation (does the recommender surface known-relevant items?)
- Portfolio optimization validation (does the portfolio include securities with known alpha?)
- Search ranking evaluation (does the ranking recover known-relevant documents?)

Does NOT apply when:
- There is no ground truth or synthetic proxy for it
- The objective function IS the ground truth (pure optimization problems like logistics routing)
- Recovery is trivially 100% (the ground truth set is smaller than the selection budget)

## Related Lessons

- [Lesson 025: Multiple Methods as Baselines](../block3/025_multiple_selection_methods_as_baselines.md) — multiple methods provide the comparison surface; ground-truth recovery provides the evaluation criterion
- [Lesson 021: Calendar as Portfolio Optimization](../block3/021_calendar_as_portfolio_optimization.md) — the optimization problem being validated here
- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — synthetic ground truth is the foundation of this validation approach
