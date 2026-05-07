# Lesson 023: Maximum Marginal Relevance for Diversity-Aware Selection

## The Lesson

Greedy Maximum Marginal Relevance (MMR) is the practical default for selecting a diverse, high-quality subset from a large pool. At each step, it picks the item that maximizes quality minus similarity to already-selected items. It runs in O(K × N) time, requires no optimization library, and naturally balances relevance against redundancy.

## Context

A calendar optimizer needed to select 13 images from 12,217 candidates. Each image had a preference score, and 512-dimensional CLIP embeddings were available for computing pairwise visual similarity. The selection needed to maximize both voter preference and visual diversity — two objectives in direct tension, since the most popular images tend to look similar.

## What Happened

1. Considered formal optimization approaches: integer programming (scipy.optimize.milp), simulated annealing, and determinantal point processes (DPPs). All are more theoretically principled than greedy but add complexity and dependencies for a 13-from-12K selection problem.
2. Chose greedy MMR for simplicity and debuggability. The algorithm: start with an empty set, iteratively add the candidate with highest marginal utility, where utility = quality - λ × max_similarity_to_selected.
3. Implemented with CLIP cosine similarity as the redundancy measure. L2-normalized the 512-dim vectors once upfront, then cosine similarity is a single dot product per pair. At each of 13 greedy steps, evaluated all ~12K remaining candidates — total work: ~160K dot products, completing in <1 second.
4. Added hard constraints on top of MMR: max 2 images per visual cluster (k=25 clusters). This provides a coarse diversity floor that MMR's continuous penalty reinforces.
5. Compared MMR output (Method E) against naive top-13 (Method A): zero overlap in the 13 selected images. MMR aggressively avoided redundancy, selecting from 10 distinct clusters instead of the 3-4 clusters that dominate the top-13.
6. MMR's objective score was lower than cluster-limited top-N (Method B) because it sacrificed more popularity for diversity. This is a feature, not a bug — it exposes a different point on the trade-off frontier.

## Key Insights

- **Greedy is fast enough for small K.** For K=13 selections from N=12K candidates, greedy MMR completes in <1 second. Simulated annealing or ILP would take longer to set up than to run. Only consider them when K is large (hundreds) or constraints are complex (multi-resource scheduling).

- **CLIP cosine similarity is an excellent redundancy measure.** Two images that look similar to a human will have high cosine similarity in CLIP space. Using the precomputed embeddings avoids any runtime feature extraction — redundancy becomes a single dot product.

- **Max-similarity is more aggressive than mean-similarity.** `max(sim(candidate, selected_i) for i in selected)` penalizes a candidate if it's similar to *any* selected image. Mean-similarity would allow near-duplicates if the candidate is dissimilar to other selections. Max is the right choice for diversity.

- **Combine hard and soft constraints.** The cluster limit (hard: max 2 per cluster) prevents gross redundancy. MMR's similarity penalty (soft: continuous cosine penalty) handles within-cluster and cross-cluster similarity that cluster membership alone can't capture.

- **MMR parameters control the trade-off.** The weights (w_pop=0.35, w_appeal=0.20, w_redundancy=0.20, w_monthfit=0.15, w_uncertainty=0.10) determine where on the quality-diversity frontier the selection lands. Making w_redundancy larger produces more diverse but less popular slates.

## Examples

```python
# Core MMR loop (simplified)
selected = []
for _ in range(13):
    best_sk, best_utility = None, -inf
    for sk in remaining:
        quality = w_pop * pref_quantile[sk] + w_appeal * appeal_quantile[sk]
        if selected:
            max_sim = max(dot(normed[sk], normed[s]) for s in selected)
            quality -= w_redundancy * max_sim
        if quality > best_utility:
            best_sk, best_utility = sk, quality
    selected.append(best_sk)
    remaining.remove(best_sk)
```

## Applicability

MMR works for any "select K diverse, high-quality items" problem:
- Search result diversification (the original MMR use case, Carbonell & Goldstein 1998)
- Recommendation diversification (avoid showing 5 similar products)
- Document summarization (select diverse, informative sentences)
- Feature selection (select informative, non-redundant features)

Does NOT apply when diversity is irrelevant (e.g., selecting the K best answers to a factual question) or when the quality-diversity trade-off needs formal guarantees (use submodular optimization or DPPs instead).

## Related Lessons

- [Calendar as Portfolio Optimization](021_calendar_as_portfolio_optimization.md) — the broader framing of collection optimization that MMR implements
- [Choosing k for Clustering](../block1/choosing_k_for_clustering.md) — the cluster structure that provides hard diversity constraints alongside MMR's soft penalty
