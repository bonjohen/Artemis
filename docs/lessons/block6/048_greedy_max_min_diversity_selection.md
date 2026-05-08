# Lesson 048: Greedy Max-Min Diversity Selection

## The Lesson

To select k items that maximally represent the diversity within a group, iteratively pick the item most distant from all already-selected items. This greedy max-min approach is O(n×k), produces near-optimal diversity in practice, and avoids the NP-hard max-dispersion problem entirely.

## Context

A cluster of 270 space photographs needed to be summarized with 1 representative image plus 5 diverse images showing the range within the cluster. The representative (closest to centroid) captures "what the cluster looks like," but the diverse set needs to show "how different things in this cluster can be." Randomly sampling 5 images would likely pick 5 similar ones from the dense core. Picking the 5 most distant from the centroid would cluster around the periphery without covering different directions of variation.

## What Happened

1. The cluster had CLIP embeddings (512-dim) for all 270 members and a precomputed distance-to-centroid for each image. The representative was trivial: pick the image with minimum centroid distance.

2. For diversity, needed to maximize the minimum pairwise distance among selected images — the "max-min dispersion" problem. The exact solution is NP-hard, but the greedy approximation has a known 1/2 approximation guarantee and runs in O(n×k) time.

3. Implemented the greedy algorithm:
   - Start with the representative in the selected set
   - For each remaining candidate, compute its minimum Euclidean distance to any already-selected image
   - Pick the candidate with the largest minimum distance
   - Repeat k times

4. Applied across all 25 clusters to generate the "spotlights" view. The algorithm ran in milliseconds per cluster, even for the largest cluster (1,411 images). Total time for all 25 clusters: under 2 seconds including embedding loads from DuckDB.

5. The diverse selections visually confirmed the algorithm's effectiveness: the 5 images covered different visual themes (e.g., in a "moon surface" cluster: close-up craters, wide-angle terrain, horizon shots, backlit silhouettes, and surface with Earth in background).

## Key Insights

- **Greedy max-min is the right default for diversity selection.** It's simple (15 lines of code), fast (O(n×k) with small constants), has a theoretical guarantee (1/2 of optimal), and produces intuitive results. More sophisticated methods (facility location, determinantal point processes) add complexity without meaningful quality improvement at these scales.
- **Start from the representative, not from a random seed.** Seeding with the centroid-closest image anchors the diverse set around the cluster's identity. Starting from a random image or the most extreme outlier would bias the selection toward one edge of the cluster.
- **Euclidean distance on normalized embeddings ≈ cosine distance.** CLIP embeddings are L2-normalized, so Euclidean distance and cosine distance are monotonically related (d² = 2 - 2·cos). Using Euclidean distance avoids recomputing cosine similarity and works directly with numpy's `np.linalg.norm`.
- **The algorithm degrades gracefully with small clusters.** If k > n, it simply returns all items. If the cluster has very little diversity (all embeddings are near-identical), the algorithm still picks the most different items, even if the differences are subtle. No special-casing needed.
- **Visual review is the real validation.** The algorithm can be verified by looking at the output — a human can tell immediately whether the 5 images cover different visual themes. No quantitative metric for "diversity" is as convincing as a 6-image contact sheet.

## Applicability

This algorithm applies to any problem requiring diverse subset selection from a metric space:
- Product recommendation diversity (show different categories, not 5 variations of the same item)
- Search result diversification (cover different intents for an ambiguous query)
- Portfolio sampling (select representative assets from each sector)
- Test case selection (cover different input regions for property-based testing)

Does NOT apply when:
- The notion of "diversity" isn't captured by embedding distance (e.g., temporal diversity, semantic diversity that embeddings miss)
- k is large relative to n (above k ≈ n/3, the greedy approximation quality degrades and exact methods may be worth the cost)
- Fairness or quota constraints apply (e.g., "at least one from each subcategory" requires constrained optimization, not pure max-min)

## Related Lessons

- [Lesson 023: Maximum Marginal Relevance](../block3/023_maximum_marginal_relevance_for_selection.md) — MMR balances relevance and diversity with a tunable lambda; max-min is the diversity-only special case (lambda=0)
- [Lesson 045: Embedding Deduplication](045_embedding_deduplication_for_image_curation.md) — deduplication removes redundancy; diversity selection highlights the remaining variation
- [Lesson 050: Connected Components for Transitive Dedup](050_connected_components_for_transitive_dedup.md) — both operate on pairwise embedding distances; components group similar items, max-min separates diverse ones
