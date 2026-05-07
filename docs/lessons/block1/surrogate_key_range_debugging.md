# Lesson: Debugging with Surrogate Key Ranges

## Problem

When investigating why multimodal clustering produced zero results, the breakthrough came from a simple query:

```sql
SELECT min(image_sk), max(image_sk) FROM feature_image_embedding;
-- min=13775, max=25991

SELECT min(image_sk), max(image_sk) FROM feature_description_embedding;
-- min=13256, max=13774
```

The ranges are perfectly adjacent and non-overlapping. This immediately revealed that the two embedding tables represent entirely different image populations — before any join logic was even examined.

## Why It Matters

Surrogate keys (auto-incrementing integers assigned during data loading) carry implicit information about *when* and *how* data was loaded. Two populations with non-overlapping key ranges were loaded at different times or from different sources. This is not something the key was designed to tell you, but it's enormously useful for debugging.

## The Technique

When a join returns fewer rows than expected (or zero), check the key ranges of both sides:

```sql
-- Step 1: Key ranges
SELECT 'table_a' as src, min(key), max(key), count(DISTINCT key) FROM table_a
UNION ALL
SELECT 'table_b' as src, min(key), max(key), count(DISTINCT key) FROM table_b;
```

Possible findings:
- **Same range, partial overlap:** Normal — some entities in one table aren't in the other
- **Same range, full overlap:** The join condition is wrong (keys exist but aren't matching)
- **Non-overlapping ranges:** The tables represent different populations entirely
- **One range contains the other:** One table is a subset; check the filtering criteria

### Step 2: Characterize the populations

Once you know the ranges, describe what's different about the entities in each range:

```sql
SELECT
    CASE WHEN image_sk BETWEEN 13256 AND 13774 THEN 'text_range'
         WHEN image_sk BETWEEN 13775 AND 25991 THEN 'clip_range' END AS population,
    count(*) as n,
    count(title) as has_title,
    sum(CASE WHEN thumb_downloaded THEN 1 ELSE 0 END) as has_thumb
FROM dim_image
GROUP BY 1;
```

This query immediately showed: text-range images have titles but no thumbnails; clip-range images have thumbnails but no titles. The join's empty result was a data fact, not a code bug.

## When This Technique Applies

- **Feature store joins:** One feature pipeline runs on images with thumbnails, another on images with text. If the populations don't overlap, the combined feature matrix has missing columns for every row.
- **Fact table joins:** Two fact tables reference the same dimension but cover different entity subsets (e.g., one covers online orders, another covers in-store orders — the customer_sk ranges might not overlap).
- **Migration debugging:** After a data migration, checking key ranges can reveal whether old and new data were loaded correctly or if there's a gap/overlap.
- **ETL validation:** If a staging table and a dimension table have different key ranges, something went wrong in the load step.

## What Surrogate Keys Tell You (Implicitly)

| Observation | Likely Cause |
|---|---|
| Non-overlapping ranges | Different source datasets or load batches |
| Gaps in sequence | Rows deleted or filtered during load |
| One range much larger | One source is much larger than the other |
| Interleaved ranges | Data loaded in alternating batches or from a merged source |
| Identical ranges | Same population, different feature extractions |

## Limitations

- **Surrogate keys are an implementation detail.** Relying on their ranges for business logic is fragile. Use this technique for debugging, not for production queries.
- **Sequence gaps don't always mean deletions.** Some databases allocate sequences in blocks, creating gaps even with no deletions.
- **Works best with monotonically assigned keys.** If keys are UUIDs or hashes, range analysis doesn't help.

## The Broader Point

When debugging data pipeline issues, **look at the data before looking at the code.** The shapes, ranges, and distributions of your tables often make the problem obvious without reading a single line of pipeline logic. Queries like `min/max/count`, `GROUP BY` on flags, and `INTERSECT`/`EXCEPT` on key columns are the fastest diagnostic tools available.
