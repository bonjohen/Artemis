# Lesson 060: Context Blocks Turn a Tool Into a Teaching Artifact

## The Lesson

Adding a brief "why this page matters" block at the top of every page in a data application transforms it from an internal tool into a self-guided case study. A single sentence of context lets a reviewer understand what they're looking at without reading documentation or having the author present to explain.

## Context

A data science portfolio project had a 10-page SPA covering images, clustering, scoring, optimization, and validation. Each page was functional — it displayed data, supported filtering, and had interactive elements. But when shared with reviewers, the first question was always "what am I looking at?" The pages assumed familiarity with the pipeline and the problem domain. A reviewer landing on the Stats page saw score distributions and Krippendorff's Alpha numbers without any indication of why those numbers mattered.

## What Happened

1. Created a minimal reusable component — `renderContextBlock(title, text)` — that returns a styled HTML block with a title and one-sentence explanation. The component is 7 lines of code.

2. Added context blocks to all 8 section pages in a single commit. Each block follows the same pattern: the title is always "Why this page matters" and the text is one sentence explaining the page's role in the overall pipeline.

3. Examples of the context text:
   - Images page: "Browse the full 12,217-image vote pool with composite preference scores, cluster assignments, and visual feature overlays."
   - Clusters page: "How CLIP embeddings group 12,217 images into 20 visually coherent themes for diversity-aware calendar selection."
   - Stats page: "Score distributions, inter-rater reliability, and bias detection metrics that validate the manufactured voting data."

4. Styled the block with a left border accent and subtle background to visually distinguish it from page content — present enough to notice, quiet enough not to dominate.

5. The same component was reused when the Curation page was added later, with zero additional design work needed.

## Key Insights

- **One sentence of context eliminates the "what am I looking at?" problem.** The most common failure mode for portfolio projects and internal dashboards is the cold-start problem: a viewer arrives with no context and has to reverse-engineer what the page is showing. A single sentence resolves this entirely.

- **Context blocks are a UI component, not documentation.** Putting the explanation in a README or wiki means the viewer has to leave the page to understand it. An inline context block travels with the content. The viewer never has to context-switch.

- **Consistency matters more than cleverness.** Every page uses the same title ("Why this page matters"), the same component, the same visual treatment. The predictability lets a reviewer develop a reading habit: glance at the top, orient, then explore. Varying the format per page would break this.

- **The reusable component pays for itself immediately.** 7 lines of code, used 9 times across 9 pages. The alternative — bespoke intro sections with different HTML structures per page — would have been more code and less consistent.

- **Write context for the person who arrives on page 5 without seeing pages 1-4.** Hash-based SPA routing means any page can be the entry point. Each context block must stand alone — it can't assume the reader has seen the homepage or understands the pipeline.

## Examples

Before (Stats page loads with no orientation):
```
[Score Distribution chart]
[Krippendorff's Alpha: 0.516]
[Bias Detection: no significant bias]
```

After (context block at top):
```
Why this page matters
Score distributions, inter-rater reliability, and bias detection
metrics that validate the manufactured voting data.

[Score Distribution chart]
[Krippendorff's Alpha: 0.516]
[Bias Detection: no significant bias]
```

## Applicability

This pattern applies to any multi-page data application shown to people who aren't its daily users: portfolio projects, internal dashboards shared across teams, client-facing analytics, and documentation sites. It does NOT apply to tools where every user is an expert who uses the page daily — there, the context block becomes visual noise.

## Related Lessons

- [Five-Minute Reviewer Path](062_five_minute_reviewer_path.md) — the reviewer path complements context blocks: the path guides which pages to visit, the blocks orient on arrival
- [Noscript Fallback for SPA SEO](064_noscript_fallback_for_spa_seo.md) — another technique for making a JS-rendered app accessible to audiences who can't run the full SPA

## Metadata

- **Category:** design
- **Block:** block7
- **Tags:** ux, case-study, portfolio, context, reusable-components
