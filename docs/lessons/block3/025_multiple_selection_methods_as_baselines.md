# Lesson 025: Multiple Selection Methods as Baselines

## The Lesson

When building an optimizer, always generate multiple candidate solutions using different methods — including at least one naive baseline. The baseline proves the optimizer adds value. The alternatives expose the trade-off frontier. Without baselines, you can't distinguish "good optimization" from "expensive way to get the same result as sorting."

## Context

A calendar optimizer needed to select 13 images from 12,217 candidates. Five selection methods were implemented: naive top-13 by popularity (Method A), popularity with cluster limits (Method B), best image per cluster (Method C), month-first greedy (Method D), and multi-objective MMR greedy (Method E). Each produces a different 13-image slate with different trade-off characteristics.

## What Happened

1. Implemented Method A (naive top-13) first as the baseline. Took 5 minutes — sort by score, take first 13. This is what a non-optimized system would produce.
2. Implemented Methods B-E, each adding one dimension of sophistication: cluster constraints (B), cluster-first diversity (C), month-fit priority (D), and multi-objective redundancy penalty (E).
3. Ran all 5 methods and compared objective scores, popularity, diversity, month-fit, and image overlap.
4. Key finding: Method A and Method E shared 0 of 13 images. The optimization genuinely selects different images — it's not just re-ordering the same top candidates.
5. Key finding: Method B (simplest constraint — max 2 per cluster on top of popularity sort) scored highest on the composite objective. The most sophisticated method (E) scored lowest because it aggressively traded popularity for diversity.
6. This comparison is the evidence that justifies the optimization work. Without it, the claim "our optimizer produces better calendars" has no backing.

## Key Insights

- **The baseline must be trivially simple.** "Sort and take top K" is the right baseline because it's what someone would do without any optimization. If your optimizer can't beat sorting, the optimization is not adding value.

- **More sophisticated doesn't mean better.** Method B (one simple constraint added to top-N) beat Method E (multi-objective greedy with CLIP similarity). Sophistication has diminishing returns when the underlying data is noisy or the objective function is approximate.

- **Zero overlap is the strongest possible evidence.** When the optimized selection shares 0 of 13 images with the naive selection, the methods are exploring genuinely different parts of the solution space. This proves the optimization is not just rearranging deck chairs.

- **The trade-off frontier is the deliverable.** The "best" method depends on how much the user values diversity vs. popularity. Presenting 5 candidates with scores lets the user make that judgment — the optimizer provides options, not answers.

- **Each method should be independently debuggable.** If Method C produces a surprising result, you can inspect it in isolation. If all methods fed into a single meta-optimizer, diagnosing problems would be much harder.

## Examples

| Method | Objective | Popularity | Diversity | Images shared with A |
|---|---|---|---|---|
| A: Top-13 | 14.19 | **4.32** | 0.77 | 13/13 |
| B: Cluster-limited | **14.26** | 4.32 | 0.85 | 11/13 |
| C: Per-cluster | 13.96 | 4.01 | **1.00** | 5/13 |
| D: Month-first | 13.22 | 3.11 | 0.62 | 3/13 |
| E: MMR greedy | 11.89 | 2.79 | 0.77 | **0/13** |

The table tells the story: each method trades popularity for a different secondary objective.

## Applicability

This lesson applies to any optimization problem where:
- The objective function has multiple components in tension
- The "right" balance is subjective or context-dependent
- Stakeholders need to justify the complexity of the optimizer

Does NOT apply to problems with a single clear objective (e.g., minimize latency) where the baseline comparison is just "faster or slower."

## Related Lessons

- [Calendar as Portfolio Optimization](021_calendar_as_portfolio_optimization.md) — the problem framing that requires multiple methods
- [Maximum Marginal Relevance](023_maximum_marginal_relevance_for_selection.md) — Method E's implementation
