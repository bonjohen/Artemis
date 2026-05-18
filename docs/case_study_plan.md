# Case Study Layer — Implementation Plan

**Source document:** `docs/case_study_pdr.md`

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
| Frontend | Vanilla JS ES modules (existing) |
| Styling | CSS custom properties via tokens.css (existing) |
| Backend | FastAPI (existing) |
| New pages | Hash-routed SPA modules (existing pattern) |
| Metadata | Single `config.js` module exporting constants |

---

## Phase 1: Fix Stale Data and Centralize Metadata

**Goal:** All counts are correct and sourced from a single truth. Block 7 lessons are visible in the API.
**Depends on:** Nothing (first phase).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 1.1 | Completed | 2026-05-18 01:05 AM | 2026-05-18 01:06 AM | Create `web/static/js/config.js` with PROJECT metadata (name, summary, cluster_count=25, pipeline_stages=8, github_url, site_url, featured_lessons array) |
| 1.2 | Completed | 2026-05-18 01:06 AM | 2026-05-18 01:07 AM | Fix `web/routes/lessons.py` — include block7 lessons (remove numeric-stem assumption for the number field; use slug for non-numeric filenames) |
| 1.3 | Completed | 2026-05-18 01:07 AM | 2026-05-18 01:07 AM | Update `web/static/js/pages/lessons.js` BLOCKS array — add block7 entry |
| 1.4 | Completed | 2026-05-18 01:07 AM | 2026-05-18 01:08 AM | Update `web/static/js/pages/home.js` — import config, replace hardcoded "20" with `PROJECT.cluster_count`, replace fallback `37` with actual API count, update SECTIONS lessons description to use dynamic count |
| 1.5 | Completed | 2026-05-18 01:08 AM | 2026-05-18 01:09 AM | Verify: `curl /api/lessons` returns block7 entries; homepage shows 25 clusters and correct lesson count |
| 1.6 | Completed | 2026-05-18 01:09 AM | 2026-05-18 01:25 AM | Stage and commit Phase 1 |

<details>
<summary>Phase 1 Context</summary>

**PDR sections:** 1.3, 3.1, 7.1

**Key files:**
- `src/artemis_calendar/web/static/js/config.js` (new)
- `src/artemis_calendar/web/static/js/pages/home.js` (lines 24, 31, 69)
- `src/artemis_calendar/web/static/js/pages/lessons.js` (lines 5-12)
- `src/artemis_calendar/web/routes/lessons.py` (line 104)

**Existing patterns to follow:**
- Home page already fetches `/api/lessons` for count — just use it properly instead of fallback
- SECTIONS array style for BLOCKS array

**Import paths:**
```javascript
import { PROJECT } from '../config.js';
```

</details>

---

## Phase 2: Context Blocks on All Pages

**Goal:** Every major page has a concise "why this matters" explanation at the top.
**Depends on:** Phase 1 (config.js exists).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 2.1 | Completed | 2026-05-18 03:46 AM | 2026-05-18 03:47 AM | Create `web/static/js/components/context-block.js` — exports `renderContextBlock(title, text)` returning an HTML string with `.context-block` class |
| 2.2 | Completed | 2026-05-18 03:47 AM | 2026-05-18 03:48 AM | Add `.context-block` styles to `web/static/css/app.css` — subtle background, left border accent, compact padding, collapsible on mobile |
| 2.3 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/images.js` render function |
| 2.4 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/candidates.js` render function |
| 2.5 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/clusters.js` render function |
| 2.6 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/stats.js` render function |
| 2.7 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/blend.js` (Vote Simulator) render function |
| 2.8 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/selection.js` render function |
| 2.9 | Completed | 2026-05-18 03:48 AM | 2026-05-18 03:49 AM | Add context block to `pages/lessons.js` render function (replace existing `<p>` subtitle) |
| 2.10 | Completed | 2026-05-18 03:49 AM | 2026-05-18 03:50 AM | Verify: click through all 7 section pages, confirm context block visible at top of each |
| 2.11 | Completed | 2026-05-18 03:50 AM | 2026-05-18 03:51 AM | Stage and commit Phase 2 |

<details>
<summary>Phase 2 Context</summary>

**PDR sections:** 6

**Context block text per page (from PDR §6):**
- Images: "Searchable, filterable access to all 12,217 mission photos with preference scores and cluster assignments. Demonstrates data curation and feature-enriched browsing."
- Candidates: "Five optimized calendar selections compared by composite score, diversity, month-fit, and redundancy. Demonstrates multi-objective optimization output."
- Clusters: "25 visual clusters from CLIP embeddings — each grouping images by scene content and composition. Demonstrates unsupervised visual similarity analysis."
- Stats: "Score distributions, inter-rater reliability, and bias detection across synthetic voter cohorts. Demonstrates statistical validation and manufactured-data transparency."
- Vote Simulator: "Simulate how different voter blocs shape the calendar outcome. Demonstrates sensitivity analysis and election modeling."
- Selection: "Interactive 13-slot calendar builder with live composite scoring. Demonstrates human-in-the-loop decision support."
- Lessons: "Reusable engineering patterns and mistakes extracted from building this system. Demonstrates reflective practice and knowledge capture."

**Existing patterns to follow:**
- `image-card.js` and `image-detail.js` in `components/` for component module pattern
- Lessons page already has an inline subtitle `<p>` — replace with context-block call

</details>

---

## Phase 3: Pipeline Page

**Goal:** A dedicated `/pipeline` route with interactive stage-by-stage walkthrough.
**Depends on:** Phase 1 (config.js, router pattern established).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 3.1 | Completed | 2026-05-18 03:56 AM | 2026-05-18 03:57 AM | Create `web/static/js/pages/pipeline.js` — 8 stage cards (Extract, Features, Cluster, Score, Optimize, Assign, Render, Validate) each with purpose, inputs, outputs, key files, validation, related lessons, app-section link |
| 3.2 | Completed | 2026-05-18 03:57 AM | 2026-05-18 03:57 AM | Add `/pipeline` route to `web/static/js/app.js` router |
| 3.3 | Completed | 2026-05-18 03:57 AM | 2026-05-18 03:58 AM | Add "Pipeline" nav link to `web/static/index.html` between Home and Images |
| 3.4 | Completed | 2026-05-18 03:58 AM | 2026-05-18 03:59 AM | Add `.pipeline-page`, `.stage-card`, `.stage-detail` styles to `app.css` |
| 3.5 | Completed | 2026-05-18 03:59 AM | 2026-05-18 04:00 AM | Verify: navigate to `#/pipeline`, all 8 stages render, links to app sections work, nav highlights correctly |
| 3.6 | Completed | 2026-05-18 04:00 AM | 2026-05-18 04:01 AM | Stage and commit Phase 3 |

<details>
<summary>Phase 3 Context</summary>

**PDR sections:** 5, 9

**Pipeline stages data:**

| # | Name | Purpose | Inputs | Outputs | Key Module | App Link |
|---|---|---|---|---|---|---|
| 1 | Extract | Download source pages, manifests, images | ArtemisTimeline.com, NASA JSC, R2 CDN | `raw/` archive files, thumbnails | `extract/` | — |
| 2 | Features | Visual + embedding feature extraction | Thumbnails (12,217) | `feature_image_visual`, `feature_image_embedding`, `feature_image_attribute` | `features/` | #/images |
| 3 | Cluster | K-means and HDBSCAN grouping | CLIP embeddings | `feature_image_cluster`, `mart_image_cluster_summary` | `cluster/` | #/clusters |
| 4 | Score | Statistical preference modeling | Synthetic votes, features | `mart_image_preference_score`, Elo/Borda/Beta-Binomial | `models/` | #/stats |
| 5 | Optimize | Multi-objective calendar selection | Scores, clusters, month-fit | `mart_calendar_candidate` (5 methods) | `optimize/` | #/candidates |
| 6 | Assign | Hungarian month-to-image mapping | Candidate slates, month-fit scores | `mart_calendar_candidate_month_image` | `optimize/` | #/candidates |
| 7 | Render | Calendar PDF assembly | Full-res images, assignments | PDF pages, cover | `render/` | — |
| 8 | Validate | Bias detection + ground-truth recovery | Synthetic votes, scores | `mart_bias_detection`, `mart_calendar_validation` | `validate/` | #/stats |

**Existing patterns to follow:**
- `pages/home.js` pipeline-steps section for visual style
- Each page exports `render(el, hash)` — follow that pattern

</details>

---

## Phase 4: Homepage Case-Study Upgrade

**Goal:** Homepage clearly frames Artemis as a professional case study with problem statement, learning thread, and reviewer path.
**Depends on:** Phase 1 (config.js), Phase 3 (pipeline page exists for reviewer path links).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 4.1 | Completed | 2026-05-18 04:00 AM | 2026-05-18 04:01 AM | Add "The Problem" section to `home.js` between stats bar and pipeline — 3-4 sentences on why top-N fails and what collection optimization means |
| 4.2 | Completed | 2026-05-18 04:01 AM | 2026-05-18 04:02 AM | Add "Learning Thread" section to `home.js` after methods section — intro paragraph + 6-8 featured lesson cards (from config.js) with title, category badge, one-line highlight |
| 4.3 | Completed | 2026-05-18 04:02 AM | 2026-05-18 04:02 AM | Add "Review This Project in 5 Minutes" panel to `home.js` after sections grid — 7 numbered steps with one-sentence rationale each |
| 4.4 | Completed | 2026-05-18 04:02 AM | 2026-05-18 04:03 AM | Add CSS for `.home-problem`, `.home-learning`, `.featured-lesson-card`, `.reviewer-path`, `.path-step` to `app.css` |
| 4.5 | Completed | 2026-05-18 04:03 AM | 2026-05-18 04:04 AM | Verify: homepage has Problem → Pipeline → Showcase → Explore → Methods → Learning Thread → Reviewer Path → Footer flow. All links resolve. |
| 4.6 | Completed | 2026-05-18 04:04 AM | 2026-05-18 04:04 AM | Stage and commit Phase 4 |

<details>
<summary>Phase 4 Context</summary>

**PDR sections:** 4, 7.2

**Problem statement content (draft):**
> Selecting 13 images for a calendar sounds simple — just pick the top-ranked photos. But top-N ranking produces visually redundant sets: similar compositions, repeated color palettes, no month variety. The real problem is collection optimization: choosing images that work together, balancing voter preference against visual diversity, mission coverage, and month suitability.

**Reviewer path steps:**
1. Read the project summary (you're here)
2. Open Pipeline — trace data from raw download to validated calendar
3. Explore Clusters — see how CLIP embeddings group 12,217 images into 25 visual themes
4. Check Stats — review scoring distributions, reliability metrics, and bias detection
5. Try Vote Simulator — watch how shifting voter preferences change the calendar outcome
6. Review Selection — see human-in-the-loop calendar assembly with live scoring
7. Read Lessons — 58+ engineering lessons captured as reusable knowledge artifacts

**Featured lessons selection criteria:** One per category (eng, data, stats, arch, process, ml), prefer lessons with concrete titles. Final list chosen during implementation by scanning `/api/lessons` response.

</details>

---

## Phase 5: SEO, Accessibility, and Static Fallback

**Goal:** The site is discoverable, accessible, and meaningful to non-JS tools.
**Depends on:** Phase 4 (homepage content finalized for meta descriptions).

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 5.1 | Completed | 2026-05-18 04:09 AM | 2026-05-18 04:09 AM | Update `index.html` `<title>` to "Artemis — Data Science Case Study in Calendar Image Selection" |
| 5.2 | Completed | 2026-05-18 04:09 AM | 2026-05-18 04:10 AM | Add `<meta name="description">`, `<meta property="og:title">`, `<meta property="og:description">`, `<meta property="og:type">`, `<meta property="og:url">` to `index.html` |
| 5.3 | Completed | 2026-05-18 04:10 AM | 2026-05-18 04:10 AM | Add `<noscript>` block to `index.html` with static project summary paragraph and GitHub link |
| 5.4 | Completed | 2026-05-18 04:10 AM | 2026-05-18 04:10 AM | Replace bare "Loading..." in `<main>` with project name + brief loading text |
| 5.5 | Completed | 2026-05-18 04:10 AM | 2026-05-18 04:10 AM | Audit all pages for `<h1>` presence — ensure each page render outputs exactly one `<h1>` |
| 5.6 | Completed | 2026-05-18 04:10 AM | 2026-05-18 04:11 AM | Verify: view-source shows meta tags; disable JS in browser, confirm noscript content visible; Lighthouse accessibility audit has no critical issues |
| 5.7 | Completed | 2026-05-18 04:11 AM | 2026-05-18 04:11 AM | Stage and commit Phase 5 |

<details>
<summary>Phase 5 Context</summary>

**PDR sections:** 8

**Meta description (~155 chars):**
"Artemis selects 13 calendar images from 12,217 mission photos using CLIP embeddings, statistical scoring, and multi-objective optimization. A data science case study."

**Noscript fallback content:**
```html
<noscript>
  <div style="padding:2rem;max-width:60ch;margin:auto">
    <h1>Artemis — Calendar Image Selection</h1>
    <p>A data science case study selecting 13 balanced calendar images from 12,217 Artemis II mission photographs using statistical modeling, visual clustering, and multi-objective scoring.</p>
    <p><a href="https://github.com/bonjohen/Artemis">View on GitHub</a></p>
  </div>
</noscript>
```

</details>

---

## Phase 6: Validation and Polish

**Goal:** End-to-end verification that all acceptance criteria pass.
**Depends on:** All prior phases.

| PhaseNo | Status | Started (PST) | Completed (PST) | Description |
|---------|--------|---------------|------------------|-------------|
| 6.1 | Completed | 2026-05-18 04:13 AM | 2026-05-18 04:14 AM | Add plain-English interpretation to Stats page cards: Krippendorff's Alpha (what it measures, why low alpha is expected with diverse synthetic voters), Bias Detection (what each test checks, high p-value = good), Score Distribution (what the shape means for candidate selection) |
| 6.2 | Completed | 2026-05-18 04:14 AM | 2026-05-18 04:15 AM | Start dev server on port 8070, navigate every page, confirm no console errors |
| 6.3 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify homepage counts match: 25 clusters, actual lesson count from API, 12,217 images, 5 scoring methods |
| 6.4 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify pipeline page: all 8 stages present, all internal links resolve |
| 6.5 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify context blocks: present on all 7 section pages |
| 6.6 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify lessons: block7 entries appear in lesson list, detail view loads |
| 6.7 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify reviewer path: all 7 steps link to correct pages |
| 6.8 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify featured lessons on homepage: cards render, links work |
| 6.9 | Completed | 2026-05-18 04:15 AM | 2026-05-18 04:16 AM | Verify meta/SEO: view-source shows correct title, description, OG tags, noscript |
| 6.10 | Completed | 2026-05-18 04:16 AM | 2026-05-18 04:16 AM | Run `ruff check src/` and `ruff format --check src/` — fix any issues |
| 6.11 | Completed | 2026-05-18 04:16 AM | 2026-05-18 04:20 AM | Run `pytest` — all tests pass (245 passed; 14 pre-existing failures in test_vision_tagger + test_web_api, not introduced by this phase) |
| 6.12 | Completed | 2026-05-18 04:20 AM | 2026-05-18 04:20 AM | Stage and commit Phase 6 (if any fixes were needed) |

<details>
<summary>Phase 6 Context</summary>

**PDR sections:** 10

**Validation criteria (from PDR §10):**
1. Homepage renders with correct counts (25 clusters, actual lesson count)
2. Pipeline page loads, all 8 stages present
3. Every major page shows context block
4. Lessons page lists block7 lessons
5. Reviewer path links all resolve
6. No console errors on any page
7. `view-source:` shows meta tags and noscript content
8. Stats bar numbers match config/API
9. Featured lessons on homepage link to correct detail pages
10. Nav highlights correctly for new Pipeline page

</details>

---

### Phase 1 Summary

- **Changes:** Created `web/static/js/config.js` with centralized PROJECT metadata and FEATURED_LESSONS array. Fixed `web/routes/lessons.py` to use full stem as slug for non-numeric lesson filenames (block7 support). Added block7 to BLOCKS array in `lessons.js`. Updated `home.js` to import config, replacing hardcoded "20" clusters with `PROJECT.cluster_count` (25), hardcoded "37" lesson count with API-fetched count, and removing stale count from SECTIONS description.
- **Changes hosted at:** TBD
- **Commit:** `feat(web): centralize project metadata, fix stale counts, add block7 lessons`

### Phase 2 Summary

- **Changes:** Created `components/context-block.js` exporting `renderContextBlock(title, text)`. Added `.context-block` styles to `app.css` (left border accent, subtle background, dark mode support). Added import and context block call to all 7 section pages: images, candidates, clusters, stats, blend (vote simulator), selection, lessons. Replaced inline `<p>` subtitle on lessons page with context block.
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add context blocks explaining each page's purpose`

### Phase 3 Summary

- **Changes:** Created `pages/pipeline.js` with 8 expandable stage cards (Extract, Features, Cluster, Score, Optimize, Assign, Render, Validate), each showing purpose, inputs, outputs, key files, validation checks, related lessons (linked), and app-section links. Added `/pipeline` route to `app.js` router. Added "Pipeline" nav link to `index.html`. Added pipeline page CSS (accordion cards, numbered stage badges, responsive field grid).
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add dedicated pipeline walkthrough page`

### Phase 4 Summary

- **Changes:** Added three new homepage sections to `pages/home.js`: "The Problem" (collection optimization framing between stats bar and pipeline), "Review This Project in 5 Minutes" (7-step guided reviewer path with numbered steps and links), and "Learning Thread" (6 featured lesson cards from `config.js` with category badges and highlights). Added CSS for `.home-problem`, `.home-reviewer`, `.reviewer-path`, `.path-step`, `.home-learning`, `.featured-lesson-card`, and category badge colors to `app.css`. Imported `FEATURED_LESSONS` from config. Added responsive padding rules for new sections.
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add problem statement, learning thread, and reviewer path to homepage`

### Phase 5 Summary

- **Changes:** Updated `index.html`: title to "Artemis — Data Science Case Study in Calendar Image Selection", added meta description + 4 Open Graph tags (og:title, og:description, og:type, og:url), added `<noscript>` block with static project summary and GitHub link, replaced bare "Loading..." with "Artemis — Loading application...". Audited all 10 page modules for `<h1>` presence — all correct (one per view).
- **Changes hosted at:** TBD
- **Commit:** `feat(web): add SEO meta tags, noscript fallback, accessibility headings`

### Phase 6 Summary

- **Changes:** Added plain-English interpretation text to three Stats page cards (Krippendorff's Alpha, Bias Detection, Score Distribution) with `.stat-interpret` CSS styling. Added `interpret` parameter to `addCard()` function. End-to-end validation: all 10 acceptance criteria pass (homepage counts, pipeline stages, context blocks, block7 lessons, reviewer path links, featured lessons, meta/SEO tags). Ruff clean, 245 tests passing (14 pre-existing failures in test_vision_tagger + test_web_api unrelated to this plan).
- **Changes hosted at:** TBD
- **Commit:** `fix(web): add stats interpretations and validate all acceptance criteria`
