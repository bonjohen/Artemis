# Lesson 062: A Guided Reviewer Path for Portfolio Projects

## The Lesson

Add a numbered "review this project in N minutes" path to the homepage of any portfolio project or case study. Without explicit guidance, reviewers wander randomly through pages and miss the strongest parts of the work. A curated path ensures every reviewer sees the same narrative arc, regardless of how much time they have.

## Context

A data science portfolio project had 10 interactive pages covering data ingestion, feature extraction, clustering, statistical scoring, optimization, calendar rendering, and validation. The work was technically strong, but reviewers (hiring managers, peers, collaborators) consistently reported not knowing where to start or what to look at. Some spent 5 minutes on the image browser (the least technically interesting page) and left without seeing the optimization or bias detection work.

## What Happened

1. Added a "Review This Project in 5 Minutes" section to the homepage — a numbered 7-step path from problem statement to lessons learned.

2. Each step has three parts: a step number, a linked page name in bold, and a one-line explanation of what to look for on that page. Example:
   - Step 3: **Explore Clusters** — see how CLIP embeddings group 12,217 images into 20 visual themes.
   - Step 5: **Try Vote Simulator** — watch how shifting voter preferences change the calendar outcome.

3. The path follows the pipeline's natural order (extract → cluster → score → optimize → validate → lessons), which matches how the project was built. This gives the reviewer a narrative arc: raw data → structure → decisions → outcomes → reflections.

4. Steps are cumulative but independent — a reviewer who only has 2 minutes can do steps 1-3 and still get a coherent story. The full 7-step path takes about 5 minutes at a brisk pace.

5. The section lives between the pipeline overview and the explore cards on the homepage, so it's visible without scrolling on most screens but doesn't block someone who wants to free-explore.

## Key Insights

- **Reviewers optimize for speed, not coverage.** A hiring manager scanning portfolios might spend 2-5 minutes per project. Without a guided path, they'll click the most obvious link (often the least interesting page) and move on. The path ensures the 2 minutes are spent on the most impressive work.

- **The path is a narrative, not a sitemap.** A sitemap lists pages; a reviewer path tells a story. Each step builds on the previous one: "you saw the raw data, now see how it was structured, now see how decisions were made." This mirrors how a live presentation would flow.

- **Name the specific thing to notice on each page.** "Open Pipeline" is vague. "Trace data from raw download through eight stages to validated calendar" tells the reviewer what to look for. The one-line description is doing the work of a slide deck's talking points.

- **Start with the problem, end with reflection.** Step 1 is "read the project summary" (the problem), step 7 is "read lessons" (the reflection). This mirrors the structure of a technical paper or case study: motivation → method → results → discussion. Reviewers unconsciously expect this arc.

- **Keep the step count under 10.** A 15-step path feels like homework. 5-7 steps is the sweet spot — substantial enough to show depth, short enough that a reviewer will actually follow it through.

## Applicability

This pattern applies to any portfolio project, internal demo, or technical case study that has multiple pages or sections. It's especially valuable when the project's strongest work is not on the most obvious page. It does NOT apply to production tools where users have specific tasks — there, task-oriented navigation is better than a guided tour.

## Related Lessons

- [Context Blocks for Case Study Narration](060_context_blocks_for_case_study_narration.md) — the per-page context blocks complement the reviewer path by orienting someone who jumps to a page mid-path

## Metadata

- **Category:** design
- **Block:** block7
- **Tags:** portfolio, ux, navigation, case-study, reviewer-experience
