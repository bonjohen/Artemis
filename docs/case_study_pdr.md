# Physical Design Requirements: Case Study Layer

**Source document:** `docs/lessons/block7/public-coding-suggestions.md`, `docs/lessons/block7/puiblic-review.md`
**Project root:** `C:\Projects\Artemis`
**Date:** 2026-05-17 (PST)

## 1. System Context

The Artemis web app at `artemis.johnboen.com` is a working data science application with 8 pages (Home, Images, Candidates, Clusters, Stats, Vote Simulator, Selection, Lessons). It demonstrates serious engineering but lacks a **case-study presentation layer** — the connective tissue that helps a technical reviewer understand *what the project is*, *why it matters*, and *what to look at* in under five minutes.

This PDR defines the physical changes to add that layer without disrupting the existing app architecture.

### 1.1 Existing Infrastructure to Reuse

| Asset | Location | Reuse |
|---|---|---|
| SPA router | `web/static/js/app.js` | Add `/pipeline` route, keep hash-based routing |
| Home page module | `web/static/js/pages/home.js` | Refactor: add case-study sections, fix counts, add reviewer path |
| Lessons API | `web/routes/lessons.py` | Extend: include block7, expose block count |
| CSS design system | `web/static/css/tokens.css`, `system.css`, `app.css` | Add new component classes |
| Index HTML shell | `web/static/index.html` | Add meta tags, noscript fallback, Pipeline nav link |
| Stats API | `web/routes/stats.py` | Extend: expose cluster_count, pipeline_stage_count |
| `_site_new/` static export | `_site_new/` | Update after changes land |

### 1.2 New Dependencies to Add

| Package | Purpose | Version Constraint |
|---|---|---|
| (none) | All work is vanilla JS + CSS + existing FastAPI | — |

### 1.3 Stale Values to Fix

| Location | Current | Correct |
|---|---|---|
| `home.js` line 69, stats bar | `20` Visual Clusters | `25` (from k=25 clustering) |
| `home.js` line 24, SECTIONS array | `37 standalone lessons` | Dynamic count from API |
| `home.js` line 31, lessonCount fallback | `37` | Should be actual count (~58 excluding block7 non-lesson files) |
| `lessons.js` BLOCKS array | 6 blocks listed | 7 blocks (missing block7) |
| `lessons.py` `_parse_lesson` | Skips non-numeric stems | block7 has descriptive filenames — need to handle |

## 2. Package Layout

No new packages. All changes are within `src/artemis_calendar/web/`:

```
web/
├── static/
│   ├── index.html              ← meta tags, noscript, nav update
│   ├── css/
│   │   └── app.css             ← new component styles (context-blocks, pipeline-page, reviewer-path)
│   └── js/
│       ├── app.js              ← add /pipeline route
│       ├── config.js           ← NEW: centralized project metadata constants
│       └── pages/
│           ├── home.js         ← refactor: case-study framing, reviewer path, featured lessons
│           ├── pipeline.js     ← NEW: dedicated pipeline walkthrough page
│           ├── lessons.js      ← add block7, fix counts
│           ├── images.js       ← add context block
│           ├── candidates.js   ← add context block
│           ├── clusters.js     ← add context block
│           ├── stats.js        ← add context block
│           ├── blend.js        ← add context block
│           └── selection.js    ← add context block
└── routes/
    ├── lessons.py              ← handle block7 filenames, expose block count
    └── stats.py                ← expose cluster_count in /api/stats
```

## 3. Data Model

No database changes. All new data is either:
- Derived from existing APIs at render time (lesson count, cluster count)
- Hardcoded in a single `config.js` metadata object (project name, summary, GitHub URL, etc.)

### 3.1 Project Metadata Object (`config.js`)

```javascript
export const PROJECT = {
  name: 'Artemis II Calendar Image Selection',
  summary: 'A data science case study in collection optimization — selecting 13 balanced calendar images from 12,217 Artemis II mission photographs using statistical modeling, visual clustering, and multi-objective scoring.',
  image_count: 12217,
  cluster_count: 25,
  scoring_methods: 5,
  selection_methods: 5,
  pipeline_stages: 8,
  github_url: 'https://github.com/bonjohen/Artemis',
  site_url: 'https://artemis.johnboen.com',
};
```

Lesson count and block count are fetched from `/api/lessons` at runtime (already done on home page, just needs to propagate).

## 4. Homepage Redesign

The homepage keeps its current visual structure (hero mosaic, stats bar, pipeline, showcase, sections, methods, footer) but adds:

1. **Case-study lede** — The `hero-lede` already frames this well. No major change needed beyond ensuring the framing is "case study" not "app."
2. **Problem statement section** — New section between stats bar and pipeline. 3-4 sentences: why top-N fails, what collection optimization means, why diversity matters.
3. **Learning Thread section** — After the methods section. 5-8 featured lesson cards linking into the lessons page. Brief intro explaining lessons as durable engineering artifacts.
4. **Reviewer Path panel** — After sections grid. "Review This Project in 5 Minutes" with 7 numbered steps, each with one-sentence rationale.
5. **Fix stats bar** — Pull cluster count from config (25), lesson count from API.

## 5. Pipeline Page

A new `/pipeline` route with a dedicated page. Each of the 8 pipeline stages gets:

| Field | Source |
|---|---|
| Stage name | Hardcoded (Extract, Features, Cluster, Score, Optimize, Assign, Render, Validate) |
| Purpose | 1-2 sentence description |
| Inputs | What enters this stage |
| Outputs | What this stage produces (tables, files, artifacts) |
| Key files | Paths in `src/artemis_calendar/` |
| Validation | What checks run |
| Related lessons | Links to 1-3 relevant lessons |
| App section | Link to the page that shows this stage's output |

Layout: vertical accordion or stacked cards. Not a static diagram — interactive and scannable.

## 6. Context Blocks ("Why This Page Matters")

Each major page gets a collapsible or always-visible block at the top:

| Page | Context Message (≤40 words) |
|---|---|
| Images | Searchable, filterable access to all 12,217 mission photos with preference scores and cluster assignments. Demonstrates data curation and feature-enriched browsing. |
| Candidates | Five optimized calendar selections compared by composite score, diversity, month-fit, and redundancy. Demonstrates multi-objective optimization output. |
| Clusters | 25 visual clusters from CLIP embeddings — each grouping images by scene content and composition. Demonstrates unsupervised visual similarity analysis. |
| Stats | Score distributions, inter-rater reliability, and bias detection across synthetic voter cohorts. Demonstrates statistical validation and manufactured-data transparency. |
| Vote Simulator | Simulate how different voter blocs shape the calendar outcome. Demonstrates sensitivity analysis and election modeling. |
| Selection | Interactive 13-slot calendar builder with live composite scoring. Demonstrates human-in-the-loop decision support. |
| Lessons | Reusable engineering patterns and mistakes extracted from building this system. Demonstrates reflective practice and knowledge capture. |

Implementation: A shared `renderContextBlock(title, text)` helper in a new `components/context-block.js` module, called at the top of each page's `render()`.

## 7. Lessons Integration

### 7.1 Block 7 Support

The lessons API currently skips files whose stems don't start with a digit. Block 7 files (`public-coding-suggestions.md`, `puiblic-review.md`) have descriptive names. Fix:
- `lessons.py`: Remove the numeric-stem assumption. Parse any `.md` that isn't `index.md` or `PLANNED.md`.
- `lessons.js` BLOCKS array: Add `{ id: 'block7', title: 'Block 7 — Public Presentation' }`.
- The `_parse_lesson` function already handles non-numeric stems (falls back to `path.stem[:3]`), so no parser changes needed.

### 7.2 Featured Lessons on Homepage

Select 6-8 lessons that demonstrate breadth (one per category). Hardcode the featured list in `config.js` as `[{block, file, highlight}]`. Render as cards with title + one-line highlight + category badge.

## 8. SEO / Static / Accessibility

| Change | File | What |
|---|---|---|
| `<title>` | `index.html` | "Artemis — Data Science Case Study in Calendar Image Selection" |
| `<meta name="description">` | `index.html` | Project summary (~155 chars) |
| `<meta property="og:*">` | `index.html` | Title, description, image (hero thumbnail), URL |
| `<noscript>` fallback | `index.html` | Static paragraph explaining what Artemis is + link to GitHub |
| Semantic headings | all pages | Ensure `<h1>` per page, `<h2>` for sections |
| Loading state | `index.html` | Replace bare "Loading..." with project name + brief text |

## 9. Navigation Update

Add "Pipeline" to the nav bar between "Home" and "Images":

```html
<a href="#/">Home</a>
<a href="#/pipeline">Pipeline</a>
<a href="#/images">Images</a>
...
```

## 10. Validation Criteria

| # | Check | Method |
|---|---|---|
| 1 | Homepage renders with correct counts (25 clusters, actual lesson count) | Browser inspection |
| 2 | Pipeline page loads, all 8 stages present | Navigate to `#/pipeline` |
| 3 | Every major page shows context block | Click through all 7 section pages |
| 4 | Lessons page lists block7 lessons | Navigate to `#/lessons`, filter |
| 5 | Reviewer path links all resolve | Click each step in the reviewer path |
| 6 | No console errors on any page | DevTools console |
| 7 | `view-source:` shows meta tags and noscript content | View source |
| 8 | Stats bar numbers match config/API | Compare home stats to `/api/stats` |
| 9 | Featured lessons on homepage link to correct detail pages | Click each |
| 10 | Nav highlights correctly for new Pipeline page | Click Pipeline link |
