# Lesson 024: Hungarian Algorithm for Optimal Assignment

## The Lesson

When you need to assign N items to N slots where each item-slot pair has a fitness score, the Hungarian algorithm gives the provably optimal assignment in O(N^3) time. For small N (≤50), it runs in microseconds and eliminates the need for greedy heuristics, manual tuning, or iterative search. Use scipy's `linear_sum_assignment` — don't implement it yourself.

## Context

A calendar optimizer selected 13 images and needed to assign each to one of 13 months (December 2026 through December 2027). Each image had a 13-element month-fit score vector (how well it suits each month). The assignment needed to maximize total month-fit — a classic assignment problem.

## What Happened

1. Initially considered greedy assignment: for each month in order, pick the best-fitting remaining image. This is simple but suboptimal — a greedy choice for January may steal the only good image for February.
2. Recognized this as the classic assignment problem (also called the bipartite matching problem). The Hungarian algorithm solves it optimally in O(N^3) time. For N=13, that's ~2,197 operations — essentially instant.
3. Used `scipy.optimize.linear_sum_assignment`, which takes a cost matrix and returns the optimal row-column assignment. Built the cost matrix as the negated month-fit matrix (scipy minimizes cost; we want to maximize fit).
4. scipy was already a de facto dependency (imported in two scoring modules for `scipy.stats.beta`) but wasn't declared in pyproject.toml. Added `scipy>=1.12` to formalize it.
5. The optimal assignment ran in <1ms for every candidate calendar. Method D (month-first greedy) achieved total month-fit of 10.5, while Method A (naive top-13 with optimal assignment) achieved 8.5. The 2-point gap shows that image selection matters more than assignment — but optimal assignment extracts every available bit of fit.
6. The same function could be reused for any future assignment problem in the project (e.g., assigning images to layout templates, or mapping clusters to review priorities).

## Key Insights

- **Greedy assignment leaves value on the table.** For a 13×13 problem, greedy typically achieves 85-95% of optimal. The remaining 5-15% is free — `linear_sum_assignment` costs one line of code and zero runtime.

- **Negate the matrix for maximization.** `linear_sum_assignment` minimizes total cost. To maximize total fit, pass `-fit_matrix` as the cost. The returned indices are the optimal assignment.

- **The cost matrix is the entire specification.** No constraints need to be expressed separately — the matrix implicitly encodes "each image gets one month, each month gets one image." Additional constraints (e.g., "image X must be in December") can be encoded by setting forbidden cells to a very high cost.

- **Small N makes algorithm choice irrelevant for runtime.** At N=13, even O(N!) brute force (6 billion assignments) would take seconds. The Hungarian algorithm matters at N=100+ where brute force is infeasible. At N=13, it matters for correctness — it's the proven optimal, not "probably good enough."

- **scipy is the right choice for one-off optimization.** Implementing the Hungarian algorithm from scratch is ~100 lines of tricky code with well-known edge cases. `scipy.optimize.linear_sum_assignment` is battle-tested and handles degenerate cases (ties, rectangular matrices) correctly.

## Examples

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

# month_fit[i] is a 13-element array of fit scores for image i
cost = np.zeros((13, 13))
for i, sk in enumerate(selected_image_sks):
    cost[i, :] = -month_fit[sk]  # negate for minimization

row_ind, col_ind = linear_sum_assignment(cost)
# row_ind[j] is the image index assigned to month col_ind[j]

total_fit = -cost[row_ind, col_ind].sum()
```

## Applicability

The Hungarian algorithm applies to any 1-to-1 assignment problem:
- Assigning employees to shifts (with preference/skill scores)
- Matching reviewers to papers (with expertise scores)
- Assigning products to shelf positions (with sales-fit scores)
- Mapping data sources to pipeline slots (with compatibility scores)

Does NOT apply when: assignments are many-to-one (use ILP instead), the objective is non-linear (use constraint programming), or N is very large (>10K — use auction algorithms or approximate methods).
