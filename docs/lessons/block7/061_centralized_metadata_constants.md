# Lesson 061: Centralize Project Metadata to Prevent Count Drift

## The Lesson

When the same project-level number (image count, cluster count, lesson count) appears in multiple frontend modules, centralize it in a single metadata object. Better still, fetch live counts from the API at render time and use the centralized constant only as a fallback. Hardcoded numbers scattered across files drift silently as the project evolves.

## Context

A data science web app had project statistics displayed on the homepage (hero text, stats bar), referenced in section card descriptions, and echoed in the guided reviewer path. The numbers — 12,217 images, 25 clusters, 53 lessons — were hardcoded in each location independently. Over several development phases, the cluster count changed from 25 to 20 (after reclustering with a dark-pixel filter), the lesson count grew from 53 to 62, and the image count had always been stable but was still duplicated in 4 places.

## What Happened

1. A code review flagged that the homepage showed "25 visual clusters" in three different places while the actual cluster API returned 20. The numbers had diverged after a reclustering phase that excluded dark frames.

2. Created `config.js` as a single-source-of-truth metadata module:
   ```javascript
   export const PROJECT = {
     image_count: 12217,
     cluster_count: 20,
     scoring_methods: 5,
     selection_methods: 5,
     pipeline_stages: 8,
   };
   ```

3. Replaced all hardcoded numbers in page modules with imports from `config.js`. The homepage hero, stats bar, section cards, and reviewer path all reference `PROJECT.cluster_count` instead of the literal `25`.

4. Added API-fetched live counts for values that change over time: lesson count from `/api/lessons`, cluster count from `/api/clusters`, dedup stats from `/api/dedup/summary`. The `PROJECT` constants serve as fallbacks when the API is unreachable.

5. Two weeks later, adding the curation page required showing duplicate counts. Because the pattern was already established, the new page fetched from the API and fell back to a sensible default — no hardcoded numbers to go stale.

## Key Insights

- **Hardcoded counts are technical debt with a silent failure mode.** When a number becomes wrong, nothing breaks — the page still renders, the layout still works. The incorrectness is only visible to someone who knows the current truth. This makes count drift harder to catch than a runtime error.

- **Centralize constants, but prefer live data.** A `config.js` object prevents *inconsistency* (different pages showing different numbers) but not *staleness* (all pages showing the same wrong number). Fetching from the API at render time prevents both. The constant is a fallback for offline/error scenarios, not the primary source.

- **The fallback pattern is `fetch().catch(() => constant)`.** Wrap API calls in try/catch with the centralized constant as the default. This gives you live accuracy when the server is up and consistent staleness when it's not — both better than scattered hardcoded values.

- **Include metadata that seems "obviously stable."** The image count (12,217) never changed, but centralizing it anyway prevented the temptation to hardcode it "just this once" in new pages. If it's a number that appears in UI text, it belongs in the metadata object.

- **Review section card descriptions when counts change.** The cluster count appeared not just in the stats bar but also in prose like "25 visual clusters grouping images by CLIP embedding similarity." Prose references are easy to miss during a data update. The fix: use template literals that reference the constant, even in descriptive text.

## Applicability

This pattern applies to any multi-page web application that displays project-level statistics. It's especially important for portfolio projects and demos where the numbers are part of the narrative — a stale number undermines the impression of rigor. It does NOT apply to one-off scripts or single-page tools where the number appears exactly once.

## Metadata

- **Category:** eng
- **Block:** block7
- **Tags:** frontend, metadata, constants, drift, single-source-of-truth
