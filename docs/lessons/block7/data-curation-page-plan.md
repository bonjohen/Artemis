# Data Curation Page — Implementation Plan

**Source document:** `docs/lessons/block7/data-curation-page-design.md`

## Work Queue Instructions

### State Transitions

Open  ──>  Started  ──>  Completed
              │
              └──>  Blocked  ──>  Started  ──>  Completed

- **Open**: Not yet begun.
- **Started**: Actively in progress. Record the start datetime (PST).
- **Completed**: Done and verified. Record the completion datetime (PST).
- **Blocked**: Cannot proceed; note the blocker in the description.

### Commit Protocol

1. Work through all tasks in a phase.
2. When every task reaches Completed, write the Phase Summary.
3. Stage and commit all changes for the phase. Do not push.
4. Proceed immediately to the next phase.

## Technology Stack (Additive)

| Concern | Choice |
|---|---|
| Frontend | Vanilla JS ES module (existing pattern) |
| Backend | FastAPI route additions to existing `dedup.py` |
| Styling | CSS custom properties via `app.css` (existing) |
| Data | DuckDB queries against `dedup_image_group`, `dedup_image_member`, `feature_image_visual` |

---

## Phase 1: Backend API Endpoints

**Goal:** Two new endpoints serve group member lists and size distribution data for the curation page.
**Depends on:** Nothing (first phase).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-18 04:37 AM | 2026-05-18 04:38 AM | Add `GET /api/dedup/groups/{group_id}/members` endpoint to `web/routes/dedup.py` — join `dedup_image_member` to `dim_image`, return `group_id`, `master_sk`, and members array (`image_sk`, `source_image_id`, `is_master`, `similarity_to_master`), ordered by `similarity_to_master` DESC, with `limit` query param (default 20, max 100) |
| 1.2 | Completed | 2026-05-18 04:37 AM | 2026-05-18 04:38 AM | Add `GET /api/dedup/distribution` endpoint to `web/routes/dedup.py` — query `dedup_image_group` for group size buckets: 2, 3-5, 6-10, 11-25, 26-50, 51-100, 101-500, 500+. Return array of `{bucket, count}` |
| 1.3 | Completed | 2026-05-18 04:37 AM | 2026-05-18 04:38 AM | Add `GET /api/dedup/dark-stats` endpoint to `web/routes/dedup.py` — count images with `dark_pixel_ratio >= 0.92` from `feature_image_visual`, return `{dark_count, threshold, total_vote_pool}` |
| 1.4 | Completed | 2026-05-18 04:38 AM | 2026-05-18 04:41 AM | Verify: `curl` all three new endpoints, confirm JSON response shape and non-empty data |
| 1.5 | Completed | 2026-05-18 04:41 AM | 2026-05-18 04:41 AM | Run `ruff check src/artemis_calendar/web/routes/dedup.py` and `ruff format --check` — fix any issues |
| 1.6 | Started | 2026-05-18 04:41 AM | | Stage and commit Phase 1 |

<details>
<summary>Phase 1 Context</summary>

**PDR sections:** Design doc §§ "New API endpoints needed"

**Tables and columns:**
- `dedup_image_group`: group_id (TEXT PK), master_image_sk (BIGINT), member_count (INTEGER), similarity_threshold (DOUBLE), dedup_run_id (TEXT)
- `dedup_image_member`: group_id (TEXT), image_sk (BIGINT), similarity_to_master (DOUBLE), is_master (BOOLEAN). PK (group_id, image_sk)
- `dim_image`: image_sk (BIGINT), source_image_id (TEXT), vote_pool_flag (BOOLEAN), is_suppressed (BOOLEAN)
- `feature_image_visual`: image_sk (BIGINT), dark_pixel_ratio (DOUBLE)

**Key queries:**

Group members:
```sql
SELECT m.image_sk, d.source_image_id, m.is_master, m.similarity_to_master
FROM dedup_image_member m
JOIN dim_image d ON m.image_sk = d.image_sk
WHERE m.group_id = ?
ORDER BY m.similarity_to_master DESC
LIMIT ?
```

Distribution:
```sql
SELECT
  CASE
    WHEN member_count = 2 THEN '2'
    WHEN member_count BETWEEN 3 AND 5 THEN '3-5'
    WHEN member_count BETWEEN 6 AND 10 THEN '6-10'
    WHEN member_count BETWEEN 11 AND 25 THEN '11-25'
    WHEN member_count BETWEEN 26 AND 50 THEN '26-50'
    WHEN member_count BETWEEN 51 AND 100 THEN '51-100'
    WHEN member_count BETWEEN 101 AND 500 THEN '101-500'
    ELSE '500+'
  END AS bucket,
  count(*) AS count
FROM dedup_image_group
GROUP BY bucket
ORDER BY min(member_count)
```

Dark stats:
```sql
SELECT count(*) FROM feature_image_visual
WHERE dark_pixel_ratio >= 0.92
```

**Existing patterns to follow:**
- Route: `web/routes/dedup.py` — existing `dedup_summary` endpoint pattern (APIRouter, get_db Depends)
- Validation: `Query(default, ge=, le=)` pattern for params

**Import paths:**
```python
from artemis_calendar.web.db import get_db
```

</details>

---

## Phase 2: Frontend Page Module and Routing

**Goal:** `#/curation` route loads a new page showing stats bar, explanation prose, method cards, top duplicate groups with expandable members, and group size distribution chart.
**Depends on:** Phase 1 (API endpoints exist).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 2.1 | Open | | | Create `web/static/js/pages/curation.js` — exports `render(el, hash)`. Fetch `/api/dedup/summary?top_groups=10`, `/api/dedup/distribution`, `/api/dedup/dark-stats` in parallel. Render: context block, `<h1>`, stats bar (total images, groups, duplicates removed, active pool), "Why Curate?" prose, 3 method cards, top groups section, distribution chart |
| 2.2 | Open | | | In `curation.js` top-groups section: render each group as a card with master thumbnail (accent border), member count, similarity threshold. Add click-to-expand that fetches `/api/dedup/groups/{group_id}/members?limit=12` and renders member thumbnails in a flex row (master highlighted, others dimmed). Cap at 12 thumbnails with "(N more)" label for large groups |
| 2.3 | Open | | | In `curation.js` distribution section: render horizontal bar chart from `/api/dedup/distribution` data — bucket labels on left, bars proportional to count, count labels on right. Same inline style pattern as stats.js score distribution |
| 2.4 | Open | | | Add `/curation` route to `web/static/js/app.js` routes object — between `/images` and `/candidates` |
| 2.5 | Open | | | Add "Curation" nav link to `web/static/index.html` — between Images and Candidates links |
| 2.6 | Open | | | Verify: navigate to `#/curation`, stats bar renders with non-zero numbers, method cards display, at least one group card expands to show member thumbnails, distribution chart has bars |
| 2.7 | Open | | | Stage and commit Phase 2 |

<details>
<summary>Phase 2 Context</summary>

**PDR sections:** Design doc §§ "Page layout", "Design decisions"

**Context block text:**
"How near-duplicate detection and dark-frame filtering reduce 12,217 mission photos to a pool of visually distinct candidates before scoring and optimization."

**Why Curate prose (from design doc):**
"Selecting 13 images for a calendar sounds simple — just pick the top-ranked photos. But the raw collection contains thousands of functionally identical frames: consecutive shots from the same camera angle, near-black images of empty space, and sequences that differ by only a few pixels. Without curation, identical frames inflate preference scores, bias cluster assignments, and waste the optimizer's budget. A calendar optimizer that sees 6,810 copies of the same dark frame will overweight that 'image' — producing a calendar dominated by redundant selections."

**Method card content:**
1. **CLIP Embedding Similarity** — "Each image is encoded as a 512-dimensional vector by CLIP ViT-B/32. Pairs with cosine similarity >= 0.98 are linked. Connected components (via scipy) group transitively similar images — if A matches B and B matches C, all three form one group, even if A and C aren't directly similar."
2. **Dark Frame Filtering** — "Pixel-level brightness analysis flags images where 92%+ of pixels fall below brightness 20 (on 0-255 scale). These near-black frames — 5,771 of 12,217 — are excluded from scoring and optimization via the ACTIVE_IMAGE_FILTER."
3. **Master Selection** — "Within each duplicate group, the image with the highest composite preference score is retained as master. Ties break on brightness. The rest are suppressed (is_suppressed flag in dim_image) — reversible via restore_all()."

**Stats bar numbers (from API):**
- Total: `summary.total`
- Groups: `summary.groups`
- Duplicates: `summary.total - summary.active` (or sum of member_count - groups)
- Dark frames: from `/api/dedup/dark-stats`

**Existing patterns to follow:**
- Page module: `pages/pipeline.js` — context block + h1 + section layout
- Method cards: `pages/home.js` — `.methods-grid` / `.method-card` pattern
- Bar chart: `pages/stats.js` — inline score distribution bars
- Expandable cards: `pages/pipeline.js` — `.stage-card` click-to-expand pattern
- Component: `components/context-block.js` — `renderContextBlock(title, text)`

**Import paths:**
```javascript
import { renderContextBlock } from '../components/context-block.js';
```

</details>

---

## Phase 3: CSS Styling

**Goal:** Curation page is visually polished, consistent with existing pages, responsive.
**Depends on:** Phase 2 (page structure exists to style).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 3.1 | Open | | | Add `.curation-stats`, `.curation-prose`, `.curation-methods`, `.curation-groups`, `.curation-group-card`, `.curation-group-header`, `.curation-group-members`, `.curation-master`, `.curation-member`, `.curation-dist` styles to `web/static/css/app.css` |
| 3.2 | Open | | | Add responsive rules for curation page — stats bar wraps on mobile, method cards stack to 1-column at 480px, group member thumbnails scroll horizontally on narrow screens |
| 3.3 | Open | | | Verify: page looks correct at desktop (1200px+), tablet (768px), and mobile (375px) widths |
| 3.4 | Open | | | Stage and commit Phase 3 |

<details>
<summary>Phase 3 Context</summary>

**Styling approach:**
- Stats bar: reuse `.home-stats` pattern (flex, centered, gap)
- Prose block: reuse `.problem-text` pattern (max-width 58ch, left-aligned)
- Method cards: reuse `.methods-grid` + `.method-card` (auto-fill grid, 240px min)
- Group cards: similar to `.spotlight-cluster` (border, rounded, overflow hidden)
- Group header: flex row with master thumb, group info, expand toggle
- Member thumbnails: flex row with overflow-x auto (horizontal scroll for large groups)
- Distribution chart: same inline bar pattern as stats.js score distribution
- Master thumbnail highlight: 2px accent border (same as `.cluster-spot-rep`)

**Responsive breakpoints (match existing):**
- 768px: stats bar tighter gap, method cards 2-col
- 480px: method cards 1-col, stats bar vertical

</details>

---

## Phase 4: Verification and Polish

**Goal:** End-to-end validation, all pages still work, no regressions.
**Depends on:** All prior phases.

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 4.1 | Open | | | Verify curation page: stats bar shows correct numbers (cross-check with `curl /api/dedup/summary`), all 3 method cards present, at least 3 group cards render with master thumbnails |
| 4.2 | Open | | | Verify group expand: click a group card, member thumbnails load, master is visually distinguished, "(N more)" appears for large groups |
| 4.3 | Open | | | Verify distribution chart: bars render, buckets match `curl /api/dedup/distribution` |
| 4.4 | Open | | | Verify nav: "Curation" link appears between Images and Candidates, highlights correctly when on `#/curation` |
| 4.5 | Open | | | Verify no regressions: click through Home, Pipeline, Images, Candidates, Clusters, Stats, Vote Simulator, Selection, Lessons — all load |
| 4.6 | Open | | | Run `ruff check src/` and `ruff format --check src/` — fix any issues |
| 4.7 | Open | | | Run `pytest` — confirm no new failures beyond pre-existing 14 |
| 4.8 | Open | | | Stage and commit Phase 4 (if any fixes needed) |

<details>
<summary>Phase 4 Context</summary>

**Validation criteria:**
1. Stats bar: 4 numbers, all > 0, total = 12,217
2. Method cards: 3 cards visible (CLIP, Dark Frame, Master Selection)
3. Group cards: 10 groups from API, master thumbnail visible on each
4. Group expand: member thumbnails load on click, master highlighted
5. Distribution chart: at least 4 bars, counts > 0
6. Nav: "Curation" link present, aria-current works
7. No console errors on curation page
8. All other pages unaffected

**Pre-existing test failures (not caused by this plan):**
- `tests/test_vision_tagger.py` — 7 failures (mock tagger)
- `tests/test_web_api.py` — 7 failures (DuckDB connection)

</details>

---

### Phase 1 Summary

- **Changes:** Added three new endpoints to `web/routes/dedup.py`: `GET /api/dedup/groups/{group_id}/members` (paginated group member list with similarity scores, master-first ordering), `GET /api/dedup/distribution` (group size histogram with 8 buckets from "2" to "500+"), `GET /api/dedup/dark-stats` (dark frame count at 0.92 threshold). All verified via curl with non-empty data.
- **Changes hosted at:** TBD
- **Commit:** `feat(api): add dedup group members, distribution, and dark-stats endpoints`

### Phase 2 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add data curation page with dedup groups and distribution`

### Phase 3 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `style(web): add curation page styles and responsive rules`

### Phase 4 Summary

- **Changes:** TBD
- **Changes hosted at:** TBD
- **Commit:** `fix(web): curation page validation and polish`
