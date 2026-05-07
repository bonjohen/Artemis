# Lesson 021: Calendar as Portfolio Optimization, Not Top-N Ranking

## The Lesson

When selecting a fixed-size collection where the items must work together (a calendar, a playlist, a portfolio, a menu), the problem is constrained set optimization — not top-N ranking. The best collection often contains none of the individually top-ranked items, because collection-level properties (diversity, coverage, balance) matter as much as individual quality.

## Context

A project needed to select 13 images for a 13-month calendar from a pool of 12,217 Artemis II mission photos. Each image had a preference score from voter data. The naive approach — pick the 13 highest-scoring images — would likely produce a visually redundant calendar (e.g., 13 similar Earth-from-orbit shots) because the most popular image types cluster together in the embedding space.

## What Happened

1. Framed the problem initially as "rank images, take top 13." This was the simplest baseline (Method A) and served as a comparison point.
2. Realized the calendar has collection-level requirements that top-N ranking ignores: visual diversity (no two images too similar), month fit (bright warm images for summer, dramatic images for December), mission coverage (launch, transit, lunar orbit, return), and a suitable cover image.
3. Designed a multi-objective utility function that scores the entire 13-image set, not individual images: preference sum + diversity bonus + month-fit sum + cover score - redundancy penalty - uncertainty penalty.
4. Implemented 5 selection methods: naive top-13 (baseline), cluster-limited top-13, best-per-cluster, month-first greedy, and multi-objective MMR greedy. Each produces a different 13-image slate.
5. Ran all 5 methods on real data. Method A (naive top-13) and Method E (MMR greedy) shared 0 of 13 images — the optimization selected entirely different images than naive ranking.
6. Method B (cluster-limited) scored highest on the objective function — it kept most of top-N's popularity while enforcing diversity through cluster constraints. Method C (per-cluster) achieved perfect diversity (1.0) but lower popularity.

## Key Insights

- **Top-N is a baseline, not a solution.** For any collection problem, implement naive top-N first — it takes 5 minutes and provides the comparison point that justifies the optimization work. But never ship it as the final answer.

- **Diversity and preference are in tension.** The most popular images tend to cluster visually (similar scenes, similar compositions). Enforcing diversity pushes the optimizer toward less popular but more distinctive images. The objective function's weights determine the trade-off.

- **Hard constraints beat soft penalties for diversity.** "Max 2 images per visual cluster" is easier to implement, explain, and verify than a continuous diversity penalty. Use hard constraints first; add soft penalties only if the constraints are too rigid.

- **Multiple methods expose the trade-off frontier.** Generating 5 candidate calendars makes the diversity-vs-popularity trade-off visible. Method A maximizes popularity. Method C maximizes diversity. The user picks the balance they want.

- **The cover image is a separate decision.** Cover suitability (visual impact, broad appeal, typography space) is different from monthly-page suitability. Selecting the cover from the 13 chosen images — not from the full pool — ensures it's already in the calendar.

## Examples

Results from 12,217 images, k=25 visual clusters:

| Method | Objective | Popularity | Diversity | Shared with Top-13 |
|---|---|---|---|---|
| A: Naive top-13 | 14.19 | **4.32** | 0.77 | 13/13 |
| B: Cluster-limited | **14.26** | 4.32 | 0.85 | 11/13 |
| C: Per-cluster | 13.96 | 4.01 | **1.00** | 5/13 |
| E: MMR greedy | 11.89 | 2.79 | 0.77 | **0/13** |

Method E selected entirely different images — it aggressively penalizes redundancy via CLIP cosine similarity.

## Applicability

This lesson applies to any "select K items from N" problem where the items interact:
- Music playlists (genre diversity, tempo flow)
- Product recommendations (category coverage, price range)
- Conference schedules (topic diversity, speaker variety)
- Investment portfolios (sector diversification, risk balance)
- Exam questions (topic coverage, difficulty distribution)

Does NOT apply when items are independent (e.g., top-10 search results where each result is consumed individually).

## Related Lessons

- [Choosing k for Clustering](../block1/choosing_k_for_clustering.md) — k=25 was chosen to give the optimizer enough diversity slack for 13 selections
- [Composite Scoring with Heterogeneous Signals](../block2/017_composite_scoring_with_heterogeneous_signals.md) — the preference scores that feed the optimizer
