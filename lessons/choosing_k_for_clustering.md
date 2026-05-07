# Lesson: Choosing k for k-Means Clustering in a Constrained Selection Problem

## Problem

We needed to cluster 12,217 Artemis II mission photos into visually distinct groups. The clusters serve a specific downstream purpose: ensuring the final 13-image calendar selection has visual diversity. The choice of k (number of clusters) directly affects whether the optimization can produce a good calendar.

## Why It Matters

k is the most important hyperparameter in k-means and one of the most commonly hand-waved. Too small and the clusters are too broad — visually different images land in the same group, defeating the diversity guarantee. Too large and many clusters have too few images to offer meaningful choice, and the optimization becomes over-constrained. For a selection problem with a fixed output size (13 images), k needs to be chosen with the output in mind, not just the input.

## The Decision: k=25

### Reasoning from the output constraint

The calendar needs 13 images. If we enforce "no two images from the same cluster" as a hard diversity constraint, then k must be ≥ 13. With k=13 we'd be forced to pick exactly one image per cluster — no slack, no room for preference or trade-offs.

With k=25, roughly half the clusters contribute an image to the calendar. This gives the optimizer freedom to skip clusters whose best images are weak, avoid clusters that are too similar to each other, and still guarantee that the 13 selections span at least 13 distinct visual neighborhoods.

### Reasoning from the data size

Common heuristics for k-means:

| Heuristic | Formula | k for n=12,217 |
|---|---|---|
| Square root | k ≈ √n | 110 |
| Half square root | k ≈ √(n/2) | 78 |
| Rule of thumb for interpretability | k = 20-30 for moderate datasets | 20-30 |

√(n/2) ≈ 78 is an upper bound for maximum statistical granularity. For our use case (interpretable groups for human selection), we want well below this ceiling. k=25 sits in the interpretability range.

### Actual cluster size distribution (k=25, visual)

```
Largest:  cluster 12 — 1,411 images (11.5%)
Median:   ~400 images
Smallest: cluster 22 — 77 images (0.6%)
```

This spread is informative:
- **Large clusters** (1,000+) represent dominant visual themes — likely dark space backgrounds and Earth-from-orbit views, which are the most common photo types in the Artemis dataset
- **Medium clusters** (200-600) are the sweet spot for selection — enough images to choose from, visually coherent
- **Small clusters** (< 100) represent rare image types — potentially high diversity value for the calendar precisely because they're unusual

### What k=25 does NOT guarantee

- **Clusters are not equally sized.** k-means minimizes total within-cluster variance, not cluster balance. The 1,411-image cluster vs 77-image cluster shows this.
- **Clusters are not semantically labeled.** Cluster 12 might be "dark space scenes" but that's interpretation, not something k-means knows.
- **k=25 is not optimal in any formal sense.** We didn't run elbow method, silhouette analysis, or gap statistic. For a downstream selection problem, the "right" k is the one that gives the optimizer enough diversity without over-constraining it — and that's a design judgment, not a statistical one.

## How k Interacts with the Calendar Objective

The calendar optimization (Phase 4) will balance multiple objectives:
- **Preference:** select images voters like
- **Diversity:** no two images too visually similar
- **Coverage:** represent different mission phases
- **Month fit:** match image mood to calendar month

Clustering feeds the diversity objective. With k=25:
- The optimizer can represent diversity as "at most 1 image per cluster" (hard constraint) or "penalize images from the same cluster" (soft penalty)
- 25 clusters means 25 visual neighborhoods to potentially draw from, with 13 selections leaving 12 clusters unused
- The unused clusters are where the optimizer trades off diversity against preference — a popular image from an already-represented cluster might beat a mediocre image from an unrepresented one

## What Would Go Wrong with Different k Values

| k | Problem |
|---|---|
| 5 | Clusters too broad — each cluster mixes visually different images. "Diversity" constraint is nearly meaningless. |
| 10 | Barely more clusters than calendar slots (13). Almost no room for the optimizer to trade diversity against preference. |
| 13 | Exactly one image per cluster required. No flexibility — the calendar is mechanically determined by which image is "best" in each cluster. |
| 50 | Many clusters with < 100 images. Some clusters may be so visually similar that distinguishing them is meaningless at calendar resolution. |
| 100 | Clusters become statistically noisy. Many near-empty clusters. Interpretability collapses — you can't look at 100 clusters and understand the visual space. |

## Broader Lesson

When k-means is used for a downstream decision (not just exploration), choose k based on the decision constraints:

1. **How many distinct groups does the decision need?** (For calendar: ≥ 13)
2. **How much slack does the decision-maker need?** (For optimization: ~2x the number of selections)
3. **How many groups can a human reviewer interpret?** (Rule of thumb: 15-30)

The intersection of these three constraints often gives a narrow range. For Artemis: ≥ 13, ~26, ≤ 30 → k=25.

Formal methods (elbow, silhouette, gap statistic) tell you where the *data* has structure. But for constrained selection problems, the *task* determines k more than the data does.
