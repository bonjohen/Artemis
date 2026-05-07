# Lesson: Disjoint Data Populations Breaking Multimodal Joins

## Problem

Multimodal clustering required images to have both CLIP image embeddings AND text embeddings. The intersection of these two sets was empty — 0 images qualified. The clustering silently logged a warning and returned 0 results. The pipeline appeared to work, but an entire analysis dimension produced no output.

## Why It Matters

When a data pipeline joins two tables and gets zero rows, the first instinct is "there's a bug in the join." But sometimes the data genuinely has no overlap, and the bug is in the assumption that it would. This lesson is about tracing data lineage to understand *why* two populations don't intersect, and designing systems that degrade gracefully when they don't.

## Root Cause Analysis

### The two populations

`dim_image` contains 12,736 images from two distinct sources:

| Population | image_sk range | Count | Source IDs | Has thumbnails | Has text |
|---|---|---|---|---|---|
| NASA editorial | 13256–13774 | 519 | `NHQ...`, `KSC-...` | No | 502 yes |
| Mission photos | 13775–25991 | 12,217 | `ART002-E-...` | Yes (all) | No |

### The selection filters

**CLIP image embeddings** selected images with `thumb_downloaded = true`:
```sql
WHERE di.thumb_downloaded = true  -- only mission photos (12,217)
```

**Text embeddings** selected images with titles or descriptions:
```sql
WHERE (di.title IS NOT NULL OR di.description IS NOT NULL)  -- only editorial (502)
```

### The causal chain

```
Mission photos  →  have thumbnails  →  get CLIP embeddings  →  no text metadata
Editorial images →  have text        →  get text embeddings  →  no thumbnails

CLIP ∩ Text = ∅
```

The two selection criteria are *anti-correlated* — satisfying one practically guarantees not satisfying the other.

## How It Was Discovered

1. Clustering ran successfully with visual and text types
2. Multimodal logged: `"No common images for multimodal clustering"`
3. Investigation queried the image_sk ranges:
   - CLIP embeddings: min=13775, max=25991
   - Text embeddings: min=13256, max=13774
   - The ranges are perfectly adjacent and non-overlapping

4. Further investigation revealed the two populations have different source naming patterns, different `vote_pool_flag` values, and completely different metadata profiles

## The Fix

Changed the multimodal clustering from requiring intersection to using union with optional components:

```python
# Before: required both CLIP and text
common_sks = sorted(set(vis_sks) & set(txt_sks))
if not common_sks:
    logger.warning("No common images for multimodal clustering")
    results[ctype] = 0
    continue

# After: CLIP is the backbone, text is optional (zero-filled when absent)
image_sks = vis_sks  # all images with CLIP embeddings
txt_rows = []
for sk in image_sks:
    if sk in txt_map:
        txt_rows.append(txt_map[sk])
    else:
        txt_rows.append(np.zeros(txt_dim, dtype=np.float32))
```

The weights were also adjusted to reflect that text is sparse and voters choose by appearance:
- Before: visual 0.60, text 0.30, metadata 0.10
- After: visual 0.80, text 0.05, metadata 0.15

## Design Patterns

### 1. Union with optional features, not intersection with required features

When combining multiple feature sets, design for the common case (some features missing) rather than the ideal case (all features present). Zero-fill or impute missing features rather than dropping entire rows.

### 2. Weight by coverage, not just importance

Even if text embeddings were theoretically valuable, they cover only 4% of the dataset (502/12,217). Giving them 30% weight means the multimodal vector is 30% noise for 96% of images. Weight should reflect both signal quality and signal availability.

### 3. Log more than warnings for zero-result joins

The original code logged a warning and continued. A better approach would also log the *sizes* of the two input sets:
```python
logger.warning(
    f"No overlap: {len(vis_sks)} CLIP embeddings, {len(txt_sks)} text embeddings, "
    f"image_sk ranges: CLIP [{min(vis_sks)}-{max(vis_sks)}], text [{min(txt_sks)}-{max(txt_sks)}]"
)
```
This would have made the diagnosis immediate instead of requiring manual investigation.

### 4. Validate assumptions about data populations early

A data quality check at the end of the load step could have caught this:
```sql
SELECT
    count(CASE WHEN thumb_downloaded AND title IS NOT NULL THEN 1 END) as both,
    count(CASE WHEN thumb_downloaded THEN 1 END) as thumbs_only,
    count(CASE WHEN title IS NOT NULL THEN 1 END) as text_only
FROM dim_image;
```
If `both = 0`, the pipeline should warn that multimodal features will have no overlap.

## Broader Lesson

When your pipeline joins data from multiple extraction paths, ask: **do those paths ever produce results for the same entity?** If the extraction criteria are different (one path selects by file availability, another by metadata presence), the intersection may be smaller than expected — possibly empty.

This pattern appears in many contexts:
- **Feature stores:** One pipeline extracts image features, another extracts text features. If they select from different subsets, the combined feature matrix has gaps.
- **Multi-modal ML:** Training a vision-language model requires paired data. If images and captions come from different sources, the pairing may not exist.
- **Data warehouse joins:** Two fact tables may reference the same dimension but at different grains or time ranges, producing unexpected NULLs on outer joins.

The fix is always the same: design for graceful degradation, weight by availability, and validate overlap assumptions early.
