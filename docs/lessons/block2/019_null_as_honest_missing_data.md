# Lesson 019: NULL as Honest Missing Data

## Problem

Several columns in the scoring output have no meaningful value for most images. Only ~200 images have Elo scores (from 2,000 pairwise votes). Only ~150 images have Borda scores (from 250 category rankings). The BTL model wasn't run at all. Fleiss' kappa and Kendall's W can't be computed with incomplete matrices. What value goes in these columns?

## Why It Matters

The wrong answer silently corrupts downstream analysis. If `btl_score` is set to 0.0 instead of NULL, a downstream query like `WHERE btl_score > 0` will correctly exclude images — but `AVG(btl_score)` will be dragged toward zero by thousands of fake zeros, and a scatter plot of btl_score vs. elo_score will show a misleading cluster at the origin. The damage is subtle and hard to detect because the data looks complete.

## Design Choice: NULL Means "Not Computed," Zero Means "Measured as Zero"

Three distinct states exist for any score column:

| State | Value | Meaning |
|---|---|---|
| Computed and positive | 0.15, 1532.0, 6.0 | The model ran and produced this estimate |
| Computed and zero | 0.0 | The model ran and the result is genuinely zero (e.g., zero pairwise wins) |
| Not computed | NULL | The model did not run for this image, or could not produce a result |

### Where this applies in Phase 3

- **`btl_score`**: NULL for all images. The BTL model was deliberately not run because the comparison graph is disconnected (lesson 014). Filling this with Elo scores would be dishonest — BTL and Elo make different assumptions and produce different estimates. Filling with zero would imply "BTL ran and found zero strength."

- **`elo_score`**: NULL for ~12,000 images that never appeared in a pairwise comparison. Non-NULL for ~200 images that did. An image with `elo_score = 1500.0` (the starting rating) appeared in comparisons but had balanced wins and losses — that's different from an image that was never compared.

- **`borda_score`**: NULL for images never ranked in a category. An image with `borda_score = 0` would be impossible under the current scheme (minimum Borda for a ranked image is 1.0), so NULL is the only correct value for unranked images.

- **`selection_rate`**: NULL for images never shown in a batch ballot (shouldn't happen with current data, but the schema handles it). An image shown 10 times and selected 0 times has `selection_rate = 0.0` — that's a real measurement, not missing data.

- **`fleiss_kappa`, `kendall_w`**: NULL because the metrics are mathematically undefined for incomplete data. Storing 0.0 would imply "measured and found to be zero agreement," which is a substantive claim we can't make.

### How downstream code should handle NULLs

The composite scoring module (`composite.py`) treats NULL signals as absent — no adjustment applied:

```python
elo_adj = ELO_WEIGHT * elo_quantiles.get(image_sk, 0.0) if elo else 0.0
```

If the image has no Elo data (`elo` is None), the adjustment is zero — the image is neither boosted nor penalized. This is the correct default: absence of evidence is not evidence of absence.

For aggregations, SQL's `AVG()` already ignores NULLs, so `AVG(elo_score)` correctly averages only over images that have Elo scores. But `COUNT(*)` vs `COUNT(elo_score)` matters — the former counts all rows, the latter counts only non-NULL values. Downstream queries should use `COUNT(column)` or `FILTER (WHERE column IS NOT NULL)` to make the distinction explicit.

## Alternatives Considered

1. **Fill with zero**: Common in ML pipelines where models need dense feature matrices. Appropriate for feature engineering (where zero-filling is a documented imputation step), inappropriate for analytical outputs where the consumer expects measured values.

2. **Fill with the column mean**: Standard imputation technique. Would make every image look average on dimensions where it has no data. Actively misleading for preference scores — "we don't know" is not the same as "average."

3. **Sentinel value (-1, -999)**: Used in some legacy systems to distinguish "missing" from "zero." Fragile — any arithmetic on the column produces garbage unless every consumer knows to filter sentinels. NULL is the database-native sentinel and SQL already handles it correctly.

4. **Separate boolean columns (has_elo_score, has_btl_score)**: Redundant with NULL checks and doubles the column count. `WHERE elo_score IS NOT NULL` is clearer than `WHERE has_elo_score = true`.

## What Was Learned

NULL is not a bug — it's a feature. The schema communicates honest uncertainty by distinguishing "not computed" from "computed as zero." The cost is that downstream code must handle NULLs (COALESCE, IS NOT NULL filters, NULL-safe aggregations), but this cost is much lower than the cost of debugging silent data corruption from fake zeros.

The general principle: **prefer honest incompleteness over plausible fabrication.** A table with NULLs forces consumers to confront what they don't know. A table with zeros lets them pretend they know more than they do.
