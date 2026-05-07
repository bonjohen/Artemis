# Lesson 014: Bradley-Terry-Luce and When to Skip It

## Problem

We have pairwise comparison data (image A beats image B) and want the best possible strength estimates. Bradley-Terry-Luce (BTL) is the textbook model for this — it's more principled than Elo. But with 2,000 comparisons across 12,217 images, we chose to skip BTL entirely. This lesson explains what BTL is and why sparsity kills it.

## Why It Matters

Choosing the right model isn't about sophistication — it's about whether the data supports the model's assumptions. BTL is better than Elo in theory, but a model that can't converge is worse than a simpler model that produces usable results.

## What Happened

<!-- reconstructed from git history (876828a) and lesson context -->

1. Designed the scoring schema with a `btl_score` column alongside `elo_score`, intending to implement both pairwise models. BTL is the textbook-superior model for pairwise comparison data.
2. Before implementing, analyzed the comparison graph structure. With 2,000 comparisons, at most ~4,000 images could appear (fewer due to repeats). The remaining 8,000+ images have zero comparisons — singleton components.
3. Computed the connectivity threshold: for a random graph on 12,217 nodes, a single connected component requires m ~ (n/2) * ln(n) ≈ 57,000 edges. We have 2,000 — off by a factor of ~28x.
4. Confirmed that BTL's MLE is non-identifiable on disconnected graphs: strengths of isolated components can be scaled arbitrarily without changing the likelihood. The optimizer would either fail to converge or produce meaningless absolute values.
5. Evaluated three workarounds: (a) run BTL on the connected component only (~200-500 images — too few), (b) Bayesian BTL with regularization (principled but the prior would be arbitrary on synthetic data), (c) copy Elo scores into the BTL column (dishonest).
6. Chose to defer: left `btl_score` as NULL across all 12,217 images. NULL means "not computed" — honest about the data's limitations. When real vote data arrives with denser pairwise coverage, BTL becomes feasible and the column is ready.

## Design Choice: Defer BTL Until Pairwise Data Reaches ~20K+

### Key terms

- **Bradley-Terry-Luce model**: A probabilistic model where each item i has a positive strength parameter pi, and the probability that i beats j is pi / (pi + pj). Given a set of observed comparisons, the parameters are estimated by maximum likelihood — find the pi values that make the observed outcomes most probable.

- **Maximum likelihood estimation (MLE)**: Find the parameter values that maximize the probability of the observed data. For BTL, this means solving a system of equations where each image's strength is proportional to its wins divided by the sum of expected competitions. The solution is typically found by iterative algorithms (MM algorithm, Newton-Raphson, or `scipy.optimize.minimize` with the log-likelihood).

- **Comparison graph connectivity**: BTL requires that the comparison graph be **strongly connected** — there must be a directed path from every item to every other item through chains of comparisons. If the graph has disconnected components, the likelihood function has no unique maximum — you can scale the strengths of one component arbitrarily without changing the likelihood. The MLE doesn't exist.

- **Thurstone-Mosteller alternative**: A related model where P(i beats j) = Phi(si - sj), using a normal CDF instead of the logistic function in BTL. Has the same connectivity requirement. Sometimes preferred when the comparison outcomes are more normally distributed, but the practical difference is small.

### Why 2,000 comparisons across 12,217 images is hopeless

Each comparison involves exactly 2 images. With 2,000 comparisons, at most 4,000 images can appear (and likely fewer due to repeats). That leaves 8,000+ images with zero comparisons — they form singleton components in the graph.

Even among the images that do appear, the graph is likely fragmented. For a random graph on n nodes with m edges, the threshold for a single connected component is m ~ (n/2) * ln(n). For n=12,217, that's about 57,000 edges — we have 2,000. The graph is nowhere near connected.

### What we'd need for BTL to work

1. **Either** ~20,000+ comparisons with good coverage (each image appears at least 3-4 times, spread across diverse opponents)
2. **Or** restrict BTL to the connected component of the comparison graph and accept that most images get no BTL score
3. **Or** use a regularized BTL variant with a prior on the strength parameters (Bayesian BTL) — essentially adding a penalty that prevents parameters from diverging for disconnected components

We chose none of these because the synthetic data is a placeholder. When real vote data arrives, pairwise coverage may be sufficient for approach (2) or (3). Until then, Elo provides usable scores and the `btl_score` column remains NULL.

## Alternatives Considered

1. **Implement BTL on the connected component only**: Would produce scores for ~200-500 images. Too few to be useful as a general scoring signal.
2. **Bayesian BTL with regularization**: Adds a prior on strength parameters to handle disconnection. Principled but adds a dependency (possibly `choix` or custom implementation) and the prior choice would be arbitrary with synthetic data.
3. **Copy Elo scores into the BTL column**: Tempting but dishonest. The columns exist so that downstream consumers can distinguish the methods.

## What Was Learned

The lesson isn't "BTL is bad" — it's "know your data's structure before choosing a model." BTL is the superior model when data supports it. The comparison graph connectivity check should be the first thing you do before fitting any pairwise model. A simple check: count the number of connected components in the comparison graph. If it's more than 1 (or worse, more than n/2), BTL won't help.

The `btl_score` column is deliberately left NULL rather than filled with Elo scores or zeros. NULL means "not computed" — it's honest about the state of the data and prevents downstream code from accidentally treating it as a real signal.
