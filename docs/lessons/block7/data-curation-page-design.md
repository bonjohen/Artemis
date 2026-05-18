---
title: "Data Curation Page Design"
number: data-curation-page-design
category: arch
block: block7
description: "Design document for the Data Curation page — explaining how near-duplicate detection, dark frame filtering, and master selection reduce 12,217 raw images to a meaningful candidate pool."
---

# Data Curation Page — Design

**Route:** `#/curation` — between Images and Candidates in nav

## What the page explains

The raw vote pool has 12,217 mission photographs, but many are functionally identical — consecutive frames from the same camera angle, or near-black images of empty space. The curation layer identifies and collapses these before scoring and optimization, ensuring the pipeline works with visually distinct candidates.

## Three curation mechanisms to present

| Mechanism | Method | Impact |
|---|---|---|
| **Near-duplicate detection** | CLIP embedding cosine similarity >= 0.98, connected components grouping | 450 groups found; 10,054 images are duplicates of 450 masters |
| **Dark image filtering** | `dark_pixel_ratio >= 0.92` (92%+ pixels below brightness 20) | 5,771 near-black images excluded |
| **Master selection** | Within each duplicate group, retain the image with the highest preference score (brightness as tiebreaker) | Best representative chosen per group |

The largest group has **6,810 members** — almost certainly consecutive dark-space frames. The top groups provide vivid visual proof of why curation matters.

## Page layout (top to bottom)

1. **Context block** — "Why this page matters" one-liner about data quality before optimization
2. **Page title** — `<h1>Data Curation</h1>`
3. **Summary stats bar** — 4 numbers: Total images (12,217), Duplicate groups (450), Near-duplicates removed (10,054), Active pool (from API)
4. **"Why Curate?" prose block** — 2-3 sentences: identical frames inflate scores, bias clustering, waste optimization budget. A calendar optimizer that sees 6,810 copies of the same dark frame will overweight that "image."
5. **How It Works** — 3 method cards (same pattern as homepage methods-grid):
   - **CLIP Embedding Similarity** — cosine similarity on 512-dim vectors, 0.98 threshold, connected components for transitive grouping
   - **Dark Frame Filtering** — pixel-level brightness analysis, 92% threshold
   - **Master Selection** — preference-score-first, brightness tiebreaker, reversible suppression
6. **Largest Duplicate Groups** — interactive section showing top 10 groups from `/api/dedup/summary?top_groups=10`. Each group rendered as a card with:
   - Master image thumbnail (highlighted border)
   - Group member count
   - A "Show members" expand that loads group member thumbnails (needs new API endpoint)
7. **Group Size Distribution** — horizontal bar chart showing the distribution of group sizes (needs new API endpoint)

## New API endpoints needed

### `GET /api/dedup/groups/{group_id}/members`

Returns member images for a group with thumbnails:

```json
{
  "group_id": "dedup_...",
  "master_sk": 24578,
  "members": [
    {"image_sk": 24578, "source_image_id": "ART002-E-10775", "is_master": true, "similarity_to_master": 1.0},
    {"image_sk": 24580, "source_image_id": "ART002-E-10777", "is_master": false, "similarity_to_master": 0.9923}
  ]
}
```

### `GET /api/dedup/distribution`

Returns group size histogram:

```json
[
  {"size": 2, "count": 280},
  {"size": "3-5", "count": 85},
  {"size": "6-10", "count": 40}
]
```

## Nav placement

`index.html` nav order: Home, Pipeline, Images, **Curation**, Candidates, Clusters, Stats, Vote Simulator, Selection, Lessons

## Files to create/modify

| File | Action |
|---|---|
| `web/static/js/pages/curation.js` | New — page module |
| `web/static/js/app.js` | Add `#/curation` route |
| `web/static/index.html` | Add nav link between Images and Candidates |
| `web/static/css/app.css` | Add `.curation-*` styles |
| `web/routes/dedup.py` | Add group members + distribution endpoints |

## Design decisions

- **No new dependencies.** Reuses existing dedup API, adds two lightweight endpoints.
- **Follows existing page patterns.** Context block, page-header h1, section grids — same as every other page.
- **Member thumbnails paginated.** The 6,810-member group can't render all at once. Show first 20 members with a "Load more" button or just cap at a representative sample (e.g., master + 5 most-similar + 5 least-similar within the group).
- **Currently 0 suppressed.** The `is_suppressed` flag has been restored, but the group data still exists. The page shows what *was* detected, not the current suppression state — framing it as "what the pipeline found" rather than "what's currently filtered." The ACTIVE_IMAGE_FILTER in queries.py handles the actual filtering at query time regardless.
