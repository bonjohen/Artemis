# Lesson 012: Bayesian Beta-Binomial Smoothing

## Problem

The Artemis vote system shows 50 random images per ballot and asks voters to pick 5 favorites. With 500 ballots across 12,217 images, most images are shown only 1-2 times. A raw selection rate of "1 out of 1 shown = 100%" is meaningless — it tells you nothing about whether the image is actually preferred. Raw rates are dominated by sampling noise at low exposure.

## Why It Matters

If you feed raw selection rates into an optimizer, it will select images that were lucky (shown once, happened to get picked) over images that were genuinely preferred but had the misfortune of being shown to a voter who preferred something else. The calendar would be built on noise, not signal.

## What Happened

<!-- reconstructed from git history (876828a) and lesson context -->

1. Started with raw selection rates (selected / shown) as the preference metric. Images shown once and selected once scored 1.0 — higher than genuinely popular images shown 50 times with a 30% selection rate.
2. Added Wilson lower-bound confidence intervals as a frequentist correction. This penalized low-exposure images appropriately but produced a single point estimate rather than a full posterior distribution. Couldn't express "how uncertain are we?" beyond the interval width.
3. Switched to a Beta-Binomial conjugate model. Chose Beta(2, 8) as the prior — encoding "assume an image has about a 20% selection rate until data says otherwise." The 20% is slightly above the 10% base rate (5 of 50) because the vote pool is pre-filtered to usable frames.
4. Verified the smoothing behavior: images with 1-2 exposures stay near the prior mean of 0.20 regardless of outcome. Images with 10+ exposures have posteriors dominated by data. The crossover happens around n=10, which matches the prior strength (a+b=10).
5. Kept Wilson lower bound as a secondary metric alongside the Bayesian posterior. Both are stored in `mart_image_preference_score` — Wilson for comparison, posterior_mean as the backbone of the composite score.
6. The posterior_mean became the primary input to the composite scoring formula, weighted at ~85% of the final score (with Elo and Borda as secondary adjustments).

## Design Choice: Beta-Binomial Conjugate Prior

We use a **Beta(2, 8) prior** combined with the observed selection data to produce a **posterior Beta distribution** for each image's true selection probability.

### Key terms

- **Beta distribution**: A continuous probability distribution on [0, 1], parameterized by two shape parameters alpha and beta. When alpha > beta, the distribution peaks above 0.5; when alpha < beta, it peaks below. It's the natural distribution for modeling probabilities.

- **Conjugate prior**: A prior distribution that, when combined with a likelihood function of a specific form, produces a posterior of the same distributional family. Beta is conjugate to the binomial likelihood — meaning if your prior is Beta(a, b) and you observe k successes in n trials, the posterior is Beta(a + k, b + n - k). No numerical integration needed; the answer is exact.

- **Beta(2, 8) parameterization**: Our prior says "before seeing any data, we believe the average image has about a 20% chance of being selected." The mean of Beta(a, b) is a/(a+b) = 2/10 = 0.20. This is slightly generous relative to the 10% base rate (5 of 50) because the vote pool has already been filtered to usable frames.

- **Posterior mean**: (alpha + selected) / (alpha + beta + shown). For an image shown 1 time and selected 1 time: (2+1)/(2+8+1) = 0.273. For an image shown 1 time and not selected: (2+0)/(2+8+1) = 0.182. Both are pulled toward the prior — the single observation barely moves the estimate.

- **Credible interval**: The Bayesian analog of a confidence interval. The 95% credible interval [lower, upper] means there's a 95% probability (given our model) that the true selection rate lies in this range. Computed via `scipy.stats.beta.ppf(0.025, alpha, beta)` and `.ppf(0.975, alpha, beta)`.

- **Wilson lower bound**: A frequentist alternative. It computes the lower bound of a confidence interval for a binomial proportion that works correctly at extreme proportions (0% or 100%) and small sample sizes. Formula: (p + z^2/2n - z * sqrt(p(1-p)/n + z^2/4n^2)) / (1 + z^2/n). We compute both Wilson and Bayesian — Wilson is a useful cross-check.

- **Exposure-adjustment**: The principle that images not shown to a voter should be treated as **missing data**, not as negative signals. An image with zero selections out of zero showings is unknown, not unpopular. The Beta prior handles this naturally — unshown images get pure prior scores with wide credible intervals.

## Alternatives Considered

1. **Raw selection rate**: Rejected. Meaningless at n=1 or n=2.
2. **Laplace smoothing (add-1)**: Equivalent to Beta(1,1) prior, which assumes a 50% base rate — too optimistic for images.
3. **Empirical Bayes**: Estimate the prior from the data. More sophisticated but harder to explain and not needed when the prior is weakly informative.
4. **Mixed-effects logistic regression**: Would account for voter random effects but requires substantially more data to fit reliably.

## What Was Learned

Bayesian smoothing is the right default for any sparse count-based metric. The conjugate prior trick makes it computationally trivial — no MCMC, no optimization, just arithmetic. The key decision is the prior strength (a + b = 10 in our case), which controls how many observations are needed to overcome the prior. With a total prior weight of 10, it takes about 10 observations for the data to dominate the prior — roughly the right amount of smoothing for our exposure levels.
