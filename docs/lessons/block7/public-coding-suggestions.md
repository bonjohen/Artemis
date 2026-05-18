# Coding Agent Instructions: Artemis Case Study and Learning Thread Upgrade

## Objective

Upgrade `artemis.johnboen.com` so it functions not only as an application, but also as a clear professional case study demonstrating:

1. data collection
2. visual image analysis
3. pipeline architecture
4. statistical evaluation
5. human-in-the-loop selection
6. engineering lessons learned
7. reusable project-learning artifacts

The goal is to make Artemis understandable to a technical reviewer, hiring manager, or potential client in under five minutes.

---

# Core Design Principle

Do not treat this as “adding more features.”

Treat this as adding a **case-study layer** over an existing technical application.

The app already has useful sections: Images, Candidates, Clusters, Stats, Vote Simulator, Selection, and Lessons. The missing piece is stronger explanation, navigation, and connective tissue between those sections.

---

# Required Planning Output

Create a phased implementation plan before making code changes.

The plan should include:

1. current-state review
2. content/data consistency fixes
3. homepage redesign
4. pipeline documentation integration
5. lessons integration
6. reviewer-path navigation
7. validation and acceptance criteria

Each phase should include:

* purpose
* files likely affected
* tasks
* acceptance criteria
* visible behavior to verify in browser

---

# Phase 1: Current-State Review

Inspect the existing site, repo structure, static assets, data files, JavaScript pages, and lessons output.

Identify:

* how the SPA routes are implemented
* where homepage content is defined
* where lesson counts are generated or hardcoded
* where cluster counts are generated or hardcoded
* where pipeline descriptions currently exist
* where navigation is defined
* whether lessons are static HTML, generated content, markdown-derived, or mixed

Create a short findings document before implementing.

## Acceptance Criteria

The agent should produce a short review describing:

* existing pages
* existing data sources
* hardcoded values
* generated values
* stale counts
* obvious inconsistencies
* files that need modification

---

# Phase 2: Fix Stale and Inconsistent Counts

Correct inconsistent project statistics before changing the design.

Known items to check:

* cluster count mismatch, such as 20 vs 25 clusters
* lesson count mismatch, such as 37 vs 58 lessons
* any stale references to image counts, candidate counts, pipeline stages, block counts, or lesson categories
* README/public-site mismatch if the public site presents outdated repo/project status

Prefer generated counts over hardcoded counts where practical.

If generated counts are not practical in the current architecture, centralize constants in one config/data file and reference them from the UI.

## Acceptance Criteria

In the browser:

* homepage count matches lessons page count
* cluster count matches the actual clustering configuration or data
* no visible page presents contradictory counts
* project status text is consistent across homepage, lessons, and README-derived content where displayed

---

# Phase 3: Add a Case-Study Landing Page Layer

Redesign the homepage so it immediately explains the project.

The top of the homepage should answer:

1. What is Artemis?
2. What problem does it solve?
3. What data does it use?
4. What pipeline processes the data?
5. What analysis does it perform?
6. What decision does it support?
7. What should a reviewer click next?

Use this framing:

> Artemis is a data and visual analysis project that selects a balanced 13-image calendar set from a large mission image collection using image metadata, visual embeddings, clustering, scoring, simulation, and human-in-the-loop review.

The homepage should make clear that this is not just an image gallery. It is a data-engineering and AI-analysis project.

## Suggested Homepage Sections

1. **Project Summary**

   * one short paragraph
   * dataset size
   * final selection goal
   * major methods used

2. **Problem**

   * selecting a small, balanced image set from a large archive
   * avoiding simple top-N ranking
   * preserving diversity, quality, and thematic coverage

3. **Pipeline**

   * ingest
   * stage
   * enrich
   * analyze
   * cluster
   * score
   * select
   * validate

4. **Analysis Methods**

   * metadata analysis
   * image feature extraction
   * CLIP/embedding-style visual analysis, if currently supported
   * clustering
   * scoring
   * vote simulation
   * selection optimization

5. **Explore the App**

   * Images
   * Candidates
   * Clusters
   * Stats
   * Vote Simulator
   * Selection
   * Lessons

6. **Learning Thread**

   * explain that the project captures reusable engineering lessons
   * link to featured lessons
   * link to the full lessons section

7. **Reviewer Path**

   * a short guided path for someone evaluating the project quickly

## Acceptance Criteria

The homepage should explain the project clearly without requiring the user to click GitHub first.

A reviewer should understand within one screen:

* what the project is
* why it matters
* what technical capabilities it demonstrates
* how to explore it

---

# Phase 4: Add “Why This Page Matters” Blocks

Each major page should include a short explanatory block near the top.

Do not add long essays. Add concise context.

## Images Page

Explain that this page demonstrates searchable, filterable, curated image data.

## Candidates Page

Explain that this page shows the narrowed pool of images under consideration for final selection.

## Clusters Page

Explain that this page demonstrates visual grouping, diversity control, and similarity analysis.

## Stats Page

Explain that this page shows quantitative evaluation, distribution checks, scoring behavior, and validation.

## Vote Simulator Page

Explain that this page models human preference, biased cohorts, ranking behavior, and selection sensitivity.

## Selection Page

Explain that this page shows final decision support: choosing a balanced set, not merely the highest-ranked images.

## Lessons Page

Explain that this page captures reusable engineering knowledge produced while building the project.

## Acceptance Criteria

Each major page should answer:

* what the page shows
* why it exists
* what engineering capability it demonstrates

---

# Phase 5: Make the Pipeline First-Class

Add a dedicated pipeline section or page.

The pipeline should be more than a static diagram. It should describe the project as a data system.

For each stage, show:

* stage name
* purpose
* inputs
* outputs
* major files/tables/artifacts
* validation checks
* related lessons
* link to relevant app section

## Suggested Pipeline Stages

1. Extract
2. Stage
3. Normalize
4. Enrich
5. Analyze
6. Cluster
7. Score
8. Select
9. Validate
10. Publish

Use the actual project structure if it differs.

## Acceptance Criteria

The site should expose a clear pipeline walkthrough.

A reviewer should be able to trace:

```text
raw image/data input → processed data → visual analysis → scoring → selection → lessons
```

---

# Phase 6: Make Lessons Central

The lessons section is one of the strongest differentiators. Treat it as a major project artifact, not a secondary page.

Add a homepage “Learning Thread” section that explains:

* the project captures lessons as durable engineering artifacts
* lessons are grouped by blocks/categories
* lessons connect implementation decisions to reusable knowledge
* lessons can be harvested by a future lessons-hub or portfolio aggregator

Add featured lessons to the homepage.

Prefer 5–8 featured lessons that represent different types of learning:

* architecture
* data pipeline
* statistics
* visual analysis
* validation
* process
* deployment
* documentation

## Acceptance Criteria

The homepage should visibly link Artemis functionality to lessons learned.

The lessons page should feel like part of the project story, not a detached document dump.

---

# Phase 7: Add a Reviewer Path

Add a visible section called something like:

```text
Review This Project in 5 Minutes
```

Suggested flow:

1. Read the project summary
2. Open Pipeline
3. Review Clusters
4. Review Stats
5. Try Vote Simulator
6. Review Selection
7. Read Featured Lessons
8. Open GitHub

Each step should include one sentence explaining why it matters.

## Acceptance Criteria

A reviewer should have an obvious guided path through the site.

This should be visible from the homepage.

---

# Phase 8: Improve Static/SEO/Fallback Content

The public site currently behaves like a JavaScript app. That is acceptable, but the project should expose enough static text for:

* link previews
* search indexing
* accessibility
* text-based review tools
* LLM-based review
* no-JavaScript fallback

Add or improve:

* page titles
* meta descriptions
* static homepage summary text
* semantic headings
* visible loading fallback text
* meaningful empty/error states

## Acceptance Criteria

Viewing the raw page or preview metadata should still reveal what Artemis is.

The site should not appear as only “Loading…” to non-JavaScript tools.

---

# Phase 9: Validation

After implementation, validate by running the site locally and checking the deployed site.

Validation must include browser-visible behavior, not just unit tests.

## Required Checks

1. homepage renders correctly
2. navigation works
3. every major page has a “why this matters” block
4. counts are consistent
5. lessons links work
6. pipeline page/section works
7. reviewer path links work
8. no broken internal links
9. no obvious console errors
10. deployed GitHub Pages site matches local expectations

## Acceptance Criteria

The implementation is not complete until the reviewer can open the deployed site and follow the guided path successfully.

---

# Design Tone

Use a professional but plain-spoken tone.

Avoid hype.

Avoid saying “AI-powered” unless the specific feature is actually implemented.

Prefer concrete phrases:

* visual clustering
* image embeddings
* selection optimization
* vote simulation
* data pipeline
* feature store
* validation
* reusable lessons
* decision support

Avoid vague phrases:

* revolutionary
* cutting-edge
* next-generation
* magic
* intelligent platform

---

# Implementation Guidance

Preserve the existing app structure unless there is a clear reason to refactor.

Prefer small, reviewable changes.

Centralize repeated project statistics.

Do not hardcode stale counts in multiple places.

Where possible, derive values from data files.

Where derivation is not practical, create a single project metadata/config source.

Suggested metadata object:

```text
project_name
project_summary
image_count
candidate_count
cluster_count
lesson_count
lesson_block_count
lesson_category_count
pipeline_stage_count
github_url
site_url
last_updated
```

Use this metadata consistently across homepage, lessons intro, footer, and project summary sections.

---

# Definition of Done

The work is done when Artemis presents as:

1. a working image-analysis application
2. a data pipeline demonstration
3. a visual/statistical analysis project
4. a human-in-the-loop selection tool
5. a professional engineering case study
6. a source of reusable lessons learned

The most important final test:

A technical reviewer should be able to visit `artemis.johnboen.com`, spend five minutes on the site, and understand why the project demonstrates serious data engineering and AI-practitioner capability.
