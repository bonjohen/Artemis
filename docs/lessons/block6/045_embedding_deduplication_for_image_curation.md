# Lesson 045: Embedding-Based Deduplication for Image Collection Curation

## The Lesson

When working with a large image collection from an automated source, assume near-duplicates dominate the pool until proven otherwise. Embedding cosine similarity with connected-component grouping reduces a collection to its unique members in minutes, but the threshold choice dramatically affects the result — and the right threshold depends on what "identical" means for your use case.

## Context

A calendar image selection project sources 12,217 mission photographs from an automated camera system. Many sequential frames capture nearly the same scene with minor differences in exposure, timing, or spacecraft orientation. Visual clustering (k-means on CLIP embeddings, k=25) groups images by broad visual similarity, but within clusters, hundreds of images may be functionally interchangeable — differing by a fraction of a degree of rotation or a slight change in lighting. This redundancy inflates cluster sizes, distorts preference scoring (identical images split votes), and makes visual review impractical.

## What Happened

1. Noticed that cluster 2 contained 270 images where approximately 250 were visually indistinguishable in thumbnails. Two specific images (ART002-E-26972 and ART002-E-26935) had a CLIP cosine similarity of 0.990 — nearly identical in the embedding space.

2. Tested different similarity thresholds against cluster 2 to calibrate:
   - 0.99 threshold: 3,966 duplicate pairs
   - 0.98 threshold: 8,655 duplicate pairs
   - 0.97 threshold: 11,906 duplicate pairs
   - 0.95 threshold: 26,908 duplicate pairs

3. Chose 0.98 as the operating threshold. At 0.99, too many visually identical images survived (different exposures of the same scene often land between 0.98 and 0.99). At 0.97, images that are merely similar — same subject but noticeably different composition — start grouping together, which loses real diversity.

4. Implemented deduplication using existing CLIP embeddings (512-dim, already computed for clustering):
   - L2-normalize all embeddings to unit vectors
   - Compute pairwise cosine similarity in batches of 1000 rows against all 12,217 columns (~560 MB peak memory)
   - Build a sparse adjacency matrix from above-threshold pairs
   - Find connected components using scipy — this correctly handles transitive chains (A~B and B~C groups A, B, C together even if A~C is below threshold)
   - For each group, pick the "master" image with the highest voter preference score, tie-breaking on brightness

5. Results were dramatic: 450 duplicate groups found, 10,054 images suppressed (82% of the collection), 2,163 unique images retained. The largest single group contained 6,810 members — one dominant visual pattern (similar orbital views) that the automated camera captured thousands of times.

6. Made suppression reversible: a `is_suppressed` boolean flag on the image dimension table, with `restore_all()` to undo an entire dedup run. Downstream queries (browse, scoring, optimization, cluster spotlights) filter on this flag. Original data is preserved — suppression is a view filter, not a deletion.

7. After dedup, individual clusters shrank from hundreds of images to 10-160 unique representatives. Cluster 2 went from 270 to 10 images. This made visual review practical — a human can meaningfully compare 10 images but not 270.

## Key Insights

- **Reuse embeddings you already have.** The CLIP embeddings computed for clustering served perfectly for deduplication. No additional feature extraction was needed — just a different operation (pairwise similarity instead of k-means) on the same vectors.

- **Connected components handle transitivity correctly.** Naive pairwise grouping misses chains: if A~B at 0.99 and B~C at 0.99 but A~C at 0.97, a pairwise approach at threshold 0.98 would create two groups ({A,B} and {B,C}) with B in both. Connected components create one group {A,B,C} and pick a single master. This is the mathematically correct model for "functionally identical."

- **The threshold is a domain decision, not a statistical one.** For a calendar where each page gets one image, 0.98 is right — you want to collapse truly redundant frames while preserving any meaningful visual difference. For a forensic imaging application where slight exposure differences matter, 0.99 might be too aggressive. Test against known-duplicate pairs in your specific collection.

- **Batch matrix multiply makes brute-force feasible.** Computing all 12,217 × 12,217 = 149M pairwise similarities sounds expensive, but with batched matrix multiplication on normalized vectors, it completes in 1-2 seconds on a modern CPU. The sparse result (only storing above-threshold pairs) keeps memory manageable. No approximate nearest-neighbor index was needed at this scale.

- **Suppression beats deletion.** Flagging images as suppressed rather than removing them means the operation is instantly reversible, the original data integrity is preserved for audit, and different threshold experiments can be compared by restoring and re-running. The cost is one boolean column and a WHERE clause in downstream queries.

- **Master selection should use the best available quality signal.** Picking the group master by highest preference score (from voter data) means the retained image is the one voters liked most among the duplicates. If no voter data exists, brightness and contrast are reasonable proxies — they favor well-exposed frames over dark or blown-out ones.

## Examples

### Before dedup

| Cluster | Images | Practical browsing? |
|---------|--------|-------------------|
| Cluster 2 | 270 | No — 250+ look identical |
| Cluster 12 | 1,810 | No — overwhelmingly redundant |
| Cluster 1 | 1,955 | No — scrolling through pages of the same scene |

### After dedup (threshold 0.98)

| Cluster | Images | Practical browsing? |
|---------|--------|-------------------|
| Cluster 2 | 10 | Yes — each image is visually distinct |
| Cluster 12 | ~80 | Yes — meaningful variety visible |
| Cluster 1 | ~120 | Yes — reviewable in a few minutes |

### Threshold sensitivity

```
Threshold  Pairs    Groups  Suppressed  Retained
0.99       varies   fewer   fewer       more unique images (conservative)
0.98       1.69M    450     10,054      2,163 (chosen)
0.97       more     more    more        fewer (aggressive)
```

## Applicability

This approach works for any collection where automated capture produces redundant entries:
- Surveillance footage frame extraction
- Satellite imagery from overlapping orbits
- Product photography with multiple angles of the same item
- Medical imaging series (multiple exposures of the same anatomy)
- Web scraping where the same image appears at different URLs

Does NOT apply when:
- Near-duplicates carry meaningful information (time-lapse analysis, exposure bracketing for HDR)
- The embedding model can't distinguish the relevant differences (low-resolution embeddings on high-detail images)
- The collection is small enough for manual review (under ~500 images, just look at them)

## Related Lessons

- [Lesson 005: Choosing k for Clustering](../block1/choosing_k_for_clustering.md) — k=25 was chosen before dedup when the collection was 12K images; post-dedup the collection is 2K and may warrant a different k
- [Lesson 023: Maximum Marginal Relevance](../block3/023_maximum_marginal_relevance_for_selection.md) — MMR greedy selection is conceptually similar to the diverse-sample selection in cluster spotlights; both maximize minimum distance to already-selected items
- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — the dedup threshold was calibrated against known-duplicate pairs, a form of ground-truth-first validation
