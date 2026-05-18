Artemis is a strong example site, but it needs a clearer “case study” layer on top of the app.

The project itself is excellent portfolio material: it has data ingestion, image feature extraction, CLIP embeddings, clustering, statistical scoring, optimization, rendering, synthetic validation, and an interactive web app. The README frames the core problem correctly as **collection optimization**, not simple top-N ranking, which is a much better story for data engineering / AI engineering credibility. ([GitHub][1])

The strongest parts are:

1. **The problem is concrete**

   Selecting 13 calendar images from 12,217 mission photos is easy to understand, but technically rich. That makes it much better than a vague “AI image analysis” demo. ([GitHub][1])

2. **The pipeline is portfolio-worthy**

   The repo presents a clear warehouse-style flow: Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports. That is exactly the kind of structure that shows mature data engineering thinking. ([GitHub][1])

3. **The site has the right application sections**

   The app exposes Images, Candidates, Clusters, Stats, Vote Simulator, Selection, and Lessons. That is the right navigation for demonstrating the full system: data, analysis, decision-making, simulation, and project learning. ([Artemis Calendar][2])

4. **The lessons are the major differentiator**

   The lessons page says there are 58 lessons across 6 blocks and 5 categories. That turns the site from “look at my app” into “look at how I think, debug, validate, and improve systems.” ([GitHub][3])

The main weakness is that the site appears to be more of an app than a guided case study. The fetched public page mostly exposes the shell/nav and “Loading…”, because the content is loaded through the JavaScript SPA. That is fine for humans in a browser, but weak for search, preview cards, accessibility, and anyone quickly evaluating the project through text-based tools. ([Artemis Calendar][2])

The biggest improvements I would make:

1. **Add a case-study landing page**

   The homepage should immediately say: problem, dataset, pipeline, methods, results, and what a reviewer should click next. The current homepage already has the right pieces — mission photos, visual clusters, scoring methods, lessons, and an eight-step pipeline — but it should be framed more explicitly as a professional case study. ([GitHub][4])

2. **Fix stale/inconsistent counts**

   I saw inconsistent numbers: README says k-means clustering with k=25, while the homepage hardcodes “20 Visual Clusters.” The lessons static page says 58 lessons, but the homepage section description still says 37 lessons. These are small but important credibility issues. ([GitHub][1])

3. **Add “Why this matters” explanations to each section**

   Each major page should have a short plain-English explanation:

   Images: “This shows searchable curated image data.”

   Clusters: “This shows computer vision grouping and diversity control.”

   Stats: “This shows reliability, scoring, bias checks, and validation.”

   Selection: “This shows human-in-the-loop optimization.”

   Lessons: “This shows engineering learning captured as reusable knowledge.”

4. **Expose the pipeline as a first-class artifact**

   The homepage has an eight-stage pipeline from Extract to Validate, but I would make that clickable. Each stage should show inputs, outputs, tables/files created, tests/validation, and related lessons. ([GitHub][4])

5. **Make the Lessons section central**

   The lessons are probably the best career asset on the site. Put a “Learning Thread” block on the homepage that says something like: “This project generated 58 reusable engineering lessons across infrastructure, statistics, architecture, process, data, and ML/vision.” Then link to 5–8 featured lessons. ([GitHub][3])

6. **Add a reviewer path**

   Add a small panel: “Review this project in 5 minutes.” Suggested path:

   Home → Pipeline → Clusters → Stats → Vote Simulator → Lessons → GitHub.

7. **Clarify public/private status**

   The GitHub page labels the repo public, but the README/license section says “Private repository. All rights reserved.” That should be cleaned up. ([GitHub][1])

My overall assessment: **this is a very good example site, but it needs a stronger executive/story layer.** The technical content is already there. The next improvement is not more functionality; it is making the site explain itself to a hiring manager, technical lead, or potential client in under five minutes.

[1]: https://github.com/bonjohen/Artemis "GitHub - bonjohen/Artemis: Artemis II calendar image selection data platform · GitHub"
[2]: https://artemis.johnboen.com/ "Artemis Calendar"
[3]: https://github.com/bonjohen/Artemis/raw/refs/heads/main/docs/lessons/lessons.html "Lessons Learned — Artemis"
[4]: https://github.com/bonjohen/Artemis/blob/main/src/artemis_calendar/web/static/js/pages/home.js "Artemis/src/artemis_calendar/web/static/js/pages/home.js at main · bonjohen/Artemis · GitHub"
