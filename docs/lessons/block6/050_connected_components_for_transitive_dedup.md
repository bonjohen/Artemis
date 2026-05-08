# Lesson 050: Connected Components for Transitive Deduplication

## The Lesson

When deduplicating by pairwise similarity, use graph connected components to group items — not naive pair-based merging. Pairwise similarity is not transitive in theory (A~B and B~C doesn't guarantee A~C), but for near-duplicates in practice, transitivity holds and connected components correctly group chains that pair-based approaches would split.

## Context

A 12,217-image collection needed deduplication before calendar selection. CLIP embeddings (512-dim) were already computed. The goal: find groups of "functionally identical" images (cosine similarity ≥ 0.98), pick one master per group, and suppress the rest. The challenge was grouping — many duplicate chains exist where A~B at 0.99 and B~C at 0.99 but A~C at only 0.97.

## What Happened

1. Computed pairwise cosine similarity in batches: 1000 rows × 12,217 columns per batch, thresholded at 0.98. Found 1,691,086 above-threshold pairs in 1.1 seconds using numpy batch matrix multiply on normalized vectors.

2. First considered naive pairwise grouping: for each pair (A,B), merge their groups. This is union-find, which is correct — but implementing it from scratch is error-prone. scipy provides `connected_components` on sparse graphs, which solves the same problem with a single function call.

3. Built a sparse adjacency matrix from the 1.69M pairs using `scipy.sparse.csr_matrix`. Made it symmetric (added both i→j and j→i edges). Called `scipy.sparse.csgraph.connected_components(adj, directed=False)`.

4. Result: 2,163 connected components, of which 450 had 2+ members (duplicate groups). The largest group had 6,810 members — a massive chain of near-identical orbital photographs.

5. For each multi-member group, selected the master image by highest voter preference score (tie-break on brightness), computed each member's similarity to the master, and stored the grouping in database tables.

6. The 6,810-member mega-group demonstrates why connected components matter: no single pair in that group necessarily has similarity ≥ 0.98 to every other member. The group is connected through chains of pairwise similarity, where each link in the chain is above threshold but end-to-end members may be well below. This is correct for the use case — the images are all "variations on a theme" even if the extremes are visually distinct.

## Key Insights

- **Sparse graph + connected components is the canonical solution.** The problem is literally "find connected components in a similarity graph." Using scipy's implementation means the algorithm is correct, tested, and efficient (near-linear in edges). Reimplementing union-find saves no time and risks bugs.
- **Batch matrix multiply makes brute-force feasible.** Computing 12K × 12K = 149 million similarities sounds expensive, but normalized vectors reduce cosine similarity to a dot product, and numpy's batch matmul processes 1000 × 12K in milliseconds. The total computation took 1.1 seconds. Approximate nearest-neighbor indices (FAISS, Annoy) are unnecessary at this scale.
- **Store both the graph structure and the similarity to master.** The `dedup_image_member` table records each member's similarity to its group's master. This allows post-hoc analysis: "are the members at similarity 0.98 actually duplicates, or should the threshold be higher?" Without per-member similarity, re-evaluating the threshold requires re-running the full computation.
- **The mega-group is a feature, not a bug.** A group of 6,810 images seems excessive, but it correctly represents an automated camera capturing thousands of nearly identical frames during one orbital phase. The connected component captures this reality: image #1 and image #6,810 may look different, but there's an unbroken chain of near-identical pairs connecting them. If you want to break this group, raise the threshold — don't patch the algorithm.
- **Symmetry matters.** The adjacency matrix must be symmetric (`adj[i,j] = adj[j,i] = 1`) for undirected connected components. Forgetting to add the reverse edges halves the edges and fragments groups incorrectly.

## Examples

### Transitive chain

```
Image A ←0.99→ Image B ←0.99→ Image C
   ↑                                ↑
   └───────────0.97─────────────────┘

Pair-based at 0.98:  {A,B} and {B,C} — B in both groups (broken)
Connected components: {A,B,C} — one group, one master (correct)
```

### Scale characteristics

```
Images:     12,217
Pairs > 0.98: 1,691,086
Components:   2,163 (450 with 2+ members)
Largest:      6,810 members
Compute time: 1.1 seconds (similarity) + 0.3 seconds (components)
```

## Applicability

Connected components for deduplication work when:
- Similarity is approximately transitive for your data (near-duplicates almost always satisfy this)
- The number of items fits in memory for pairwise computation (up to ~50K items with batch matrix multiply)
- Groups should be maximal — you want all transitively connected items in one group

Does NOT apply when:
- Similarity is explicitly non-transitive (e.g., "A is similar to B in color, B is similar to C in shape" — different similarity dimensions)
- You need overlapping groups (connected components produce a partition)
- Scale exceeds memory for pairwise computation (>100K items may need approximate methods)

## Related Lessons

- [Lesson 045: Embedding Deduplication](045_embedding_deduplication_for_image_curation.md) — the full deduplication workflow that uses this algorithm
- [Lesson 048: Greedy Max-Min Diversity Selection](048_greedy_max_min_diversity_selection.md) — the complementary problem: components group similar items, max-min separates diverse ones
- [Lesson 023: Maximum Marginal Relevance](../block3/023_maximum_marginal_relevance_for_selection.md) — MMR uses a similar pairwise distance computation for quality-diversity tradeoff in calendar selection
