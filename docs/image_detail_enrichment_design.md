# Image Detail Enrichment — Design Document

## 1. Purpose

The image detail modal currently shows a minimal view: thumbnail, rank, source ID, 8 numeric scores, cluster link, and calendar candidate names. The full data model has far more information per image — CLIP-identified attributes, capture metadata, camera settings, visual features, dominant colors, dedup group membership, voting statistics, and text analysis. This design enriches the modal to show "everything we can tie to an image."

## 2. Scope

Enrich the existing image detail modal (`web/static/js/components/image-detail.js`) and its backing API endpoint (`GET /api/images/{sk}` via `web/queries.py:fetch_image_detail`) to surface all available per-image data, organized into logical sections.

## 3. Current State

### What the modal shows today

| Section | Fields |
|---|---|
| Header | Rank, source_image_id |
| Image | Thumbnail |
| Scores | Preference, Elo, Borda, Broad Appeal, Uncertainty, Brightness, Contrast, Saturation |
| Context | Cluster link, calendar candidate names |

### What exists in the database but is NOT shown

| Table | Available Fields |
|---|---|
| `dim_image` | title, description, photographer, location, camera, settings, taken_at_str, vote_pool_flag, is_suppressed |
| `feature_image_visual` | orientation, aspect_ratio, dominant_color_json, has_earth_flag, has_moon_flag, has_crew_flag, has_spacecraft_flag, aesthetic_tag_json |
| `feature_image_attribute` | ~37 base + 8 derived attributes with confidence scores and accepted/tentative/rejected classification |
| `mart_image_preference_score` | polarization_score, pairwise_wins, pairwise_losses, selection_rate, shown_count, selected_count, wilson_lower, cover_fit_score |
| `feature_image_cluster` | cluster_label, distance_to_centroid |
| `dedup_image_group` / `dedup_image_member` | group_id, is_master, similarity_to_master, member_count |
| `mart_calendar_candidate_month_image` | month_label, sequence_number, month_fit_score per candidate |

## 4. Enriched Modal Layout

The modal should be organized into collapsible sections, top to bottom:

### Section 1: Identity & Capture Metadata
- **Title** (if available) — large text
- **Description** (if available) — paragraph below title
- **Capture time** — `taken_at_str` from dim_image
- **Photographer** — from dim_image
- **Location** — from dim_image
- **Camera** — camera model from dim_image
- **Settings** — ISO, aperture, shutter speed from dim_image.settings

### Section 2: Identified Attributes (CLIP Vision)
- Tag cloud or pill list of all accepted attributes, grouped by type (celestial, environment, hardware, crew, event, media)
- Tentative attributes shown in a muted style
- Each pill shows confidence score on hover
- Derived attributes (earth_and_moon, spacewalk, etc.) shown separately with a "derived" label

### Section 3: Visual Analysis
- **Orientation** — landscape/portrait/square
- **Aspect ratio** — numeric
- **Brightness / Contrast / Saturation** — bars or gauges
- **Dominant colors** — 5 color swatches from dominant_color_json with proportion labels
- **Detection flags** — Earth, Moon, Crew, Spacecraft (from visual features, legacy)

### Section 4: Preference & Voting
- **Rank** — overall position
- **Preference score** (posterior mean) with credible interval [lower, upper]
- **Elo / Borda** — side by side
- **Broad Appeal / Polarization** — opposing metrics
- **Selection rate** — selected_count / shown_count with raw counts
- **Pairwise record** — wins / losses
- **Wilson lower bound** — conservative estimate
- **Cover fit score** — suitability as calendar cover

### Section 5: Cluster & Similarity
- **Cluster ID** — link to cluster page
- **Cluster label** — human-readable name
- **Distance to centroid** — how typical this image is within its cluster
- **Dedup status** — if in a dedup group: group size, whether master, similarity to master

### Section 6: Calendar Context
- For each calendar candidate that includes this image:
  - Candidate name (link), assigned month, month fit score

## 5. API Changes

### `fetch_image_detail` in `web/queries.py`

Expand the main query to JOIN additional tables:

```sql
SELECT
    d.image_sk, d.source_image_id, d.title, d.description,
    d.photographer, d.location, d.camera, d.settings, d.taken_at_str,
    d.is_suppressed,
    p.posterior_mean, p.posterior_lower, p.posterior_upper,
    p.broad_appeal_score, p.uncertainty_score, p.polarization_score,
    p.elo_score, p.borda_score, p.cover_fit_score,
    p.pairwise_wins, p.pairwise_losses,
    p.selection_rate, p.shown_count, p.selected_count, p.wilson_lower,
    v.brightness_score, v.contrast_score, v.saturation_score,
    v.orientation, v.aspect_ratio, v.dominant_color_json,
    v.has_earth_flag, v.has_moon_flag, v.has_crew_flag, v.has_spacecraft_flag,
    v.aesthetic_tag_json,
    c.cluster_id, c.cluster_label, c.distance_to_centroid
FROM dim_image d
LEFT JOIN mart_image_preference_score p ...
LEFT JOIN feature_image_visual v ...
LEFT JOIN feature_image_cluster c ...
WHERE d.image_sk = ?
```

Add separate queries for:
1. **Attributes**: `SELECT attribute_code, confidence_score, classification, label_source FROM feature_image_attribute WHERE image_sk = ? AND is_accepted = true ORDER BY confidence_score DESC`
2. **Dedup membership**: `SELECT dm.group_id, dm.is_master, dm.similarity_to_master, dg.member_count FROM dedup_image_member dm JOIN dedup_image_group dg ON dm.group_id = dg.group_id WHERE dm.image_sk = ?`
3. **Calendar assignments**: `SELECT candidate_name, month_label, sequence_number, month_fit_score FROM mart_calendar_candidate_month_image WHERE image_sk = ? ORDER BY candidate_name, sequence_number`

### Response shape

```json
{
  "image_sk": 14000,
  "source_image_id": "abc-123",
  "rank": 42,
  "title": "Earth from lunar orbit",
  "description": "A view of Earth...",
  "taken_at_str": "2025-09-15T12:30:00Z",
  "photographer": "NASA",
  "location": "Lunar orbit",
  "camera": "Nikon D6",
  "settings": "ISO 200, f/8, 1/500s",
  "scores": {
    "preference": 0.82, "preference_lower": 0.75, "preference_upper": 0.89,
    "elo": 1650, "borda": 45,
    "broad_appeal": 0.71, "polarization": 0.15, "uncertainty": 0.08,
    "selection_rate": 0.23, "shown_count": 150, "selected_count": 35,
    "pairwise_wins": 12, "pairwise_losses": 3,
    "wilson_lower": 0.17, "cover_fit": 0.65
  },
  "visual": {
    "brightness": 0.45, "contrast": 0.62, "saturation": 0.38,
    "orientation": "landscape", "aspect_ratio": 1.5,
    "dominant_colors": [{"rgb": [20, 40, 80], "proportion": 0.35}, ...],
    "flags": {"earth": true, "moon": false, "crew": false, "spacecraft": true}
  },
  "attributes": [
    {"code": "earth", "confidence": 0.95, "type": "celestial_body"},
    {"code": "orbital", "confidence": 0.88, "type": "environment"},
    ...
  ],
  "derived_attributes": ["earth_only"],
  "cluster": {"id": 7, "label": "Earth orbital views", "distance_to_centroid": 0.23},
  "dedup": {"group_id": "g-42", "is_master": true, "similarity_to_master": 1.0, "group_size": 3},
  "calendar_assignments": [
    {"candidate": "method_e", "month": "March 2027", "sequence": 4, "month_fit": 0.82}
  ]
}
```

## 6. Frontend Changes

### `image-detail.js`

Replace the current flat layout with a sectioned modal:
- Each section has a header and content area
- Attribute pills use color coding by type (celestial = blue, environment = green, hardware = orange, crew = purple, event = red, media = gray)
- Dominant color swatches rendered as small `<div>` blocks with inline background-color
- Score bars for preference/brightness/etc. with fill proportional to value
- Metadata fields show "—" when null (camera, settings, etc. are often null for vote-pool images)

### `app.css`

Add styles for:
- `.detail-section` with header
- `.attr-pill` with type-based color variants
- `.color-swatch` for dominant colors
- `.score-bar` with fill
- `.dedup-badge` for dedup status

## 7. Files to Modify

| File | Change |
|---|---|
| `src/artemis_calendar/web/queries.py` | Expand `fetch_image_detail` query, add attribute/dedup/calendar sub-queries |
| `src/artemis_calendar/web/routes/images.py` | Update response construction if needed |
| `src/artemis_calendar/web/static/js/components/image-detail.js` | Rebuild modal with sectioned layout |
| `src/artemis_calendar/web/static/css/app.css` | Add detail modal section styles |

## 8. Data Availability Notes

Most vote-pool images (12,217) will have:
- All visual features (brightness, contrast, saturation, orientation, dominant colors)
- All CLIP attributes (37 base + 8 derived)
- Preference scores and voting stats
- Cluster assignment
- Dedup group membership (if in a group)

Most vote-pool images will NOT have:
- title, description (only 502 editorial images have text)
- photographer, location, camera, settings (metadata from source — may be sparse)
- taken_at_str (depends on source data)

The modal should gracefully hide sections with no data rather than showing empty fields.
