# Calendar Optimization Design Document

## Phase 4: Calendar Slate Generation

**Date:** 2026-05-07
**Status:** Stage 1 Design
**Inputs:** Phase 3 preference scores (12,217 images), visual features, CLIP embeddings, k=25 clusters

---

## 1. Purpose

Select 13 images that work as a calendar collection (Dec 2026 – Dec 2027), assign each to a month, and pick a cover. This is constrained portfolio optimization, not top-N ranking. The optimizer must balance voter preference, visual diversity, month fit, and coverage while penalizing redundancy.

## 2. Scope

Build `src/artemis_calendar/optimize/` module with:
- Month suitability scoring (visual-only heuristic)
- Cover suitability scoring
- Five selection methods (A–E from calendar_design.md)
- Month assignment via Hungarian algorithm
- Calendar scoring and comparison
- Warehouse storage of candidate calendars

## 3. Core Design Principles

1. **Collection over individuals.** The objective function scores the entire 13-image set, not individual images.
2. **Visual-only month fit.** Vote-pool images have no text metadata. Month assignment uses color temperature, brightness, content flags, and visual drama.
3. **CLIP-based redundancy.** Pairwise cosine similarity from precomputed CLIP embeddings is the continuous redundancy signal. Cluster membership is a hard constraint (max 2 per visual cluster).
4. **Multiple methods, shared assignment.** Each selection method produces 13 image_sks. Month assignment and cover selection are shared post-processing.
5. **Baselines required.** Naive top-13 baselines (by posterior_mean, by Elo, by broad_appeal) are mandatory for comparison.

## 4. Data Available

| Source Table | Rows | Key Columns for Optimization |
|---|---|---|
| `mart_image_preference_score` | 12,217 | posterior_mean, broad_appeal_score, uncertainty_score, polarization_score, elo_score, borda_score |
| `feature_image_visual` | 12,217 | brightness_score, contrast_score, saturation_score, dominant_color_json, has_earth_flag, has_moon_flag, has_crew_flag, has_spacecraft_flag |
| `feature_image_embedding` | 12,217 | embedding_vector (CLIP 512-dim FLOAT[]) |
| `feature_image_cluster` | 12,217 (visual) | cluster_id, distance_to_centroid (visual type, latest run) |

## 5. Month Suitability Scoring

Each image gets a 13-element month-fit vector. Scoring is heuristic based on visual features.

### 5.1 Color Temperature

Extract dominant color HSV hue from `dominant_color_json`. Map to warm_score ∈ [0,1]:
- Warm hues (0–60°, 300–360° — reds, oranges, yellows): warm_score → 1.0
- Cool hues (180–260° — blues, cyans): warm_score → 0.0
- Neutral (60–180°, 260–300°): warm_score → 0.5
- Low-saturation images (< 0.15): warm_score → 0.5 (neutral, avoid penalizing space scenes)

### 5.2 Month Profiles

Each month has a target profile:

| Month | Brightness | Warmth | Drama | Notes |
|---|---|---|---|---|
| Dec 2026 | low | cool | high | Launch/beginning, dramatic |
| Jan 2027 | low | cool | medium | Deep space, cool |
| Feb 2027 | low | cool | medium | Transit |
| Mar 2027 | medium | neutral | medium | Approaching Moon |
| Apr 2027 | medium | neutral | high | Lunar operations, drama |
| May 2027 | medium | warm | medium | Return begins |
| Jun 2027 | high | warm | low | Summer, bright |
| Jul 2027 | high | warm | low | Summer |
| Aug 2027 | high | warm | medium | Late summer |
| Sep 2027 | medium | neutral | medium | Transition |
| Oct 2027 | medium | cool | medium | Autumn |
| Nov 2027 | low | cool | medium | Pre-winter |
| Dec 2027 | low | cool | high | Closing, dramatic |

Month-fit score = 1 - weighted_distance(image_features, month_profile), normalized to [0,1].

### 5.3 Content Flag Bonuses

- has_earth_flag: +bonus for April (Earth Day) and months needing "home" feeling
- has_moon_flag: +bonus for March-April (lunar approach/orbit)
- has_crew_flag: +bonus for cover-candidate months
- has_spacecraft_flag: +bonus for launch month (Dec 2026) and return (May 2027)

## 6. Cover Suitability Scoring

Cover score per image:

```
cover_fit = 0.50 * broad_appeal_quantile
          + 0.30 * visual_impact_quantile
          + 0.10 * contrast_quantile
          + 0.10 * saturation_quantile
```

Where visual_impact = contrast_score × saturation_score. All quantile-ranked to [0,1].

## 7. Selection Methods

### Method A: Top Popularity Baseline
Sort by posterior_mean descending, take top 13.

### Method B: Popularity with Cluster Limits
Sort by posterior_mean descending. Select greedily, skipping images from visual clusters that already have 2 images. Continue until 13 selected.

### Method C: Top Per Cluster
Take top 13 visual clusters by mean_preference_score. Select best image from each.

### Method D: Month-First
For each of 13 months, find the image with the best month_fit_score (subject to cluster constraint: max 2 per cluster). Use greedy assignment.

### Method E: Multi-Objective Greedy (MMR)
Iteratively select 13 images maximizing marginal utility:

```
utility(candidate, selected_set) = 
    w_pop * posterior_mean_quantile
  + w_appeal * broad_appeal_quantile  
  + w_monthfit * best_available_month_fit
  - w_redundancy * max_cosine_similarity(candidate, selected_set)
  - w_uncertainty * uncertainty_quantile
```

Default weights: w_pop=0.35, w_appeal=0.20, w_monthfit=0.15, w_redundancy=0.20, w_uncertainty=0.10.

At each step, compute utility for all remaining candidates against the current selected set. The redundancy term uses CLIP cosine similarity (dot product of L2-normalized 512-dim vectors).

Hard constraint: max 2 images per visual cluster.

## 8. Month Assignment

After selecting 13 images, assign to months optimally.

Build a 13×13 cost matrix: `cost[i][j] = -month_fit_score[image_i][month_j]`. Solve with `scipy.optimize.linear_sum_assignment` (Hungarian algorithm). This is the provably optimal assignment.

## 9. Cover Selection

From the 13 selected+assigned images, pick the one with highest cover_fit_score. Store as cover_image_sk on the candidate.

## 10. Calendar Scoring

Score each complete candidate calendar:

```
calendar_score = 
    sum(posterior_mean for all 13)                    # preference
  + diversity_bonus                                    # cluster spread
  + sum(month_fit_score for each assignment)           # month fit
  + cover_fit_score                                    # cover quality
  - max_pairwise_similarity * redundancy_weight        # redundancy
  - sum(uncertainty_score for all 13) * uncertainty_weight  # risk
```

Diversity bonus = number of distinct visual clusters represented / 13.

## 11. Output Tables

### `mart_calendar_candidate`

| Column | Type | Description |
|---|---|---|
| candidate_run_id | TEXT | Run identifier |
| candidate_name | TEXT | Method name (method_a, method_b, ...) |
| cover_image_sk | BIGINT | Selected cover image |
| objective_score | DOUBLE | Total calendar utility |
| popularity_score | DOUBLE | Sum of posterior_mean |
| diversity_score | DOUBLE | Cluster diversity |
| month_fit_score | DOUBLE | Sum of month-fit scores |
| cover_fit_score | DOUBLE | Cover image fit |
| redundancy_penalty | DOUBLE | Max pairwise similarity |
| uncertainty_penalty | DOUBLE | Sum of uncertainty |
| created_at | TIMESTAMPTZ | |

Primary key: (candidate_run_id, candidate_name)

### `mart_calendar_candidate_month_image`

| Column | Type | Description |
|---|---|---|
| candidate_run_id | TEXT | Run identifier |
| candidate_name | TEXT | Method name |
| sequence_number | INTEGER | 1–13 |
| month_label | TEXT | "December 2026" through "December 2027" |
| image_sk | BIGINT | Assigned image |
| month_fit_score | DOUBLE | Image-month fit |
| preference_score | DOUBLE | Image posterior_mean |
| created_at | TIMESTAMPTZ | |

Primary key: (candidate_run_id, candidate_name, sequence_number)

## 12. Module Structure

```
src/artemis_calendar/optimize/
    __init__.py       # run_calendar_optimization(conn) orchestrator
    month_fit.py      # Month suitability scoring
    cover_fit.py      # Cover suitability scoring
    methods.py        # Methods A–E selection
    assignment.py     # Month assignment via Hungarian algorithm
    scoring.py        # Calendar-level scoring
    marts.py          # Write candidates to warehouse
```

## 13. Dependencies

Add `scipy>=1.12` to `pyproject.toml` under `[project.optional-dependencies] ml`. Already used by `models/batch_scores.py` and `models/composite.py`.

## 14. CLI

Add `optimize` subcommand to `cli.py`:
```
artemis-pipeline optimize [--methods a,b,c,d,e] [--seed 42]
```

## 15. Verification

1. `pytest` passes (new tests + existing 68)
2. `ruff check` and `ruff format --check` clean
3. 5 candidate calendars generated with distinct image selections
4. Each candidate has exactly 13 images, each assigned to one month
5. No image appears in two months within the same candidate
6. Method E selects different images than Method A (optimization adds value)
7. All candidates have calendar-level scores for comparison
