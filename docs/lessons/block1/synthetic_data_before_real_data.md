# Lesson: Building with Synthetic Data Before Real Data Arrives

## Problem

The Artemis project needed voter preference data to build its statistical models and calendar optimizer. But real vote data from ArtemisTimeline.com wasn't yet available — the vote export hadn't been requested, and the site's API only exposes aggregate leaderboards, not raw ballots.

Rather than wait, the project generated synthetic vote data with known properties to build and validate the pipeline end-to-end.

## Why It Matters

Data pipelines that are built without data tend to be fragile. The developer makes assumptions about data shapes, volumes, and distributions that don't survive contact with real data. Synthetic data lets you build and test the entire pipeline — from ingestion through modeling to output — while the real data is still being sourced.

## What Happened

<!-- reconstructed from git history (84e911d, 3234106) and design documents -->

1. Needed voter preference data to build statistical models and a calendar optimizer. Real vote data from ArtemisTimeline.com wasn't available — the vote export hadn't been requested, and the site's API only exposes aggregate leaderboards, not raw ballots.
2. Wrote a design document (`docs/synthetic_vote_pdr.md`) specifying synthetic voter profiles with intentional biases: 60% neutral, 20% visual-drama seekers, 10% position-biased, 10% random. The biases were chosen to test whether the pipeline could detect known patterns.
3. Implemented a seed-based generator producing three vote types matching the real voting modes: batch ballots (pick 5 from 50), pairwise comparisons (head-to-head), and category rankings (top 3). Each type preserves natural grain — raw votes, not collapsed scores.
4. Generated ground truth via deterministic hash-based latent quality scores per image. Timeline images get a +0.15 boost, category showcases get +0.25. Stored in `synthetic_image_truth` — kept separate from model inputs, usable only for post-hoc evaluation.
5. Ran the full pipeline end-to-end: 100 voters, 500 ballots, 2,000 pairwise votes, 250 category rankings. Schema validation passed, all fact tables populated, downstream models (Phase 3) ran successfully against synthetic data.
6. The synthetic data became permanent scaffolding — Phase 3 (Elo, Beta-Binomial, Borda) and Phase 4 (calendar optimization) were both developed and validated against it. When real data arrives, the pipeline switches seamlessly because the schema is identical.

## What Was Built

### Synthetic voter profiles (4 bias types)

```python
BIAS_PROFILES = {
    "earth_lover": {"earth_weight": 2.0, "space_weight": 0.5},
    "tech_focused": {"hardware_weight": 2.0, "scenery_weight": 0.5},
    "balanced": {"all_weights": 1.0},
    "contrarian": {"popular_penalty": 0.5, "unpopular_bonus": 1.5},
}
```

100 synthetic voters with explicit bias profiles. The biases are intentional and known — this lets the bias detection tests verify that the pipeline can detect each type.

### Three vote types matching the real voting modes

| Vote type | Real-world source | Synthetic implementation |
|---|---|---|
| Batch ballots | "Pick 5 from 50" | Random batch of 50 images, top 5 by voter's weighted score |
| Pairwise votes | Head-to-head Elo | Random pairs, winner determined by voter's preference |
| Category rankings | "Top 3 in category" | Category-filtered, top 3 by voter's weighted score |

Each type has its own fact table (`fact_batch_ballot`, `fact_pairwise_vote`, `fact_category_ranking`) preserving the natural grain of the vote — not collapsed into a single score.

### Ground truth for validation

```python
# synthetic_image_truth: known "true quality" for each image
# Generated from a latent quality model with noise
true_quality = base_quality + category_bonus + random_noise
```

Because the synthetic data has a known ground truth, the statistical models (Phase 3) can be validated against it: does the Elo system converge to the true ranking? Does the Bayesian model recover the ground truth scores? Do the bias profiles produce detectable patterns?

## What This Enabled

1. **End-to-end pipeline testing** — Every pipeline step from extraction through clustering runs on real-shaped data, even though the votes are synthetic
2. **Schema validation** — The vote fact tables, voter dimensions, and session tables were designed and tested before real data existed
3. **Model development** — Phase 3 (statistical modeling) can be developed and tested using synthetic data with known ground truth
4. **Bias detection development** — The intentional bias profiles provide a test harness for the bias detection system
5. **Performance benchmarking** — 100 voters × 500 ballots = 2,500 ballot-image records — enough to profile query performance without real data

## Design Decisions

### Natural grain preservation

The synthetic generator creates votes at the same grain as the real voting interface:
- Batch ballots: session → batch of 50 → 5 selections (not: per-image scores)
- Pairwise: session → pair → winner (not: win/loss counts)
- Rankings: session → category → ordered list (not: rank scores)

This forces the downstream models to aggregate from raw votes, exactly as they'll need to with real data.

### Surrogate voter keys

Voters are identified by `voter_sk` (surrogate integer) and `source_voter_id` (salted hash of a synthetic ID). This matches the privacy-preserving design for real voters — the pipeline never stores identifiable voter information.

### Seed-based reproducibility

```bash
artemis-pipeline generate-votes --seed 42 --voters 100 --ballots 500
```

Same seed = same synthetic data. This makes tests deterministic and lets developers reproduce issues.

## What Synthetic Data Cannot Validate

- **Real data quality issues:** Missing fields, encoding errors, malformed JSON, duplicate records. Real data always has surprises.
- **Distribution assumptions:** Synthetic voters follow programmed distributions. Real voters have unpredictable behavior — herding effects, time-of-day biases, mobile-vs-desktop differences.
- **Scale-specific issues:** 100 voters with 500 ballots is not 10,000 voters with 50,000 ballots. Performance and statistical properties change with scale.
- **Data freshness and staleness:** The synthetic data is static. Real data arrives in batches, may be delayed, and may be partially updated.

## Broader Lesson

When real data isn't available, generate synthetic data that:

1. **Matches the real schema exactly** — same tables, same columns, same types, same grain
2. **Has known ground truth** — so models can be validated against something
3. **Includes intentional anomalies** — so validation checks can be tested
4. **Is reproducible** — seed-based generation for deterministic tests
5. **Is clearly labeled** — the `synthetic_image_truth` table and `dim_voter.is_synthetic` flag make it impossible to confuse synthetic and real data

The synthetic data should be treated as scaffolding, not as a permanent fixture. When real data arrives, the pipeline should switch seamlessly — if it can't, that reveals assumptions that need fixing.
