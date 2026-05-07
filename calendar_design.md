# Design Document

## Artemis II 13-Month Calendar Image Selection and Page Layout

**Document status:** Companion design document
**Project:** Artemis II 2027 Calendar Image Selection
**Purpose:** Define how to select 13 calendar images, assign them to months from **December 2026 through December 2027**, choose one of those images as the cover, and generate printable 8.5x11 portrait calendar pages.

---

# 1. Calendar Product Definition

The calendar will contain:

1. A cover page.
2. Thirteen monthly calendar pages.
3. Monthly coverage from **December 2026 through December 2027**.
4. Thirteen selected images total.
5. One image assigned to each month.
6. One of the thirteen monthly images reused as the cover image.
7. A printable 8.5x11 portrait layout for every page.

The cover image will be selected from the thirteen monthly images using a defined popularity metric. The cover is not a fourteenth image.

---

# 2. Core Design Problem

The project needs to select thirteen images that work as a collection, not simply the top thirteen images by raw popularity.

The selected set should satisfy four goals:

1. Each image should be individually strong.
2. The full set should be visually diverse.
3. Each image should fit its assigned month.
4. One image should be strong enough to serve as the cover.

The selection problem has two linked decisions:

1. Which thirteen images should be included?
2. Which image should be assigned to each month?

The cover decision is made after the thirteen monthly images are selected and assigned.

---

# 3. Calendar Date Range

The calendar months are:

| Slot | Month          |
| ---: | -------------- |
|    1 | December 2026  |
|    2 | January 2027   |
|    3 | February 2027  |
|    4 | March 2027     |
|    5 | April 2027     |
|    6 | May 2027       |
|    7 | June 2027      |
|    8 | July 2027      |
|    9 | August 2027    |
|   10 | September 2027 |
|   11 | October 2027   |
|   12 | November 2027  |
|   13 | December 2027  |

---

# 4. Image Selection Methods

The system should support multiple data-driven selection methods. Each method should produce a candidate thirteen-image calendar slate. These candidate slates can then be compared.

---

## 4.1 Method A: Top Popularity Baseline

This is the simplest baseline.

Selection rule:

1. Rank all eligible images by a chosen popularity metric.
2. Select the top thirteen.
3. Assign months using month-fit scores.
4. Choose the highest-ranked image among the thirteen as the cover.

Possible popularity metrics:

1. Batch selection rate.
2. Elo score.
3. Bradley-Terry-Luce score.
4. Borda score.
5. Bayesian posterior preference score.
6. Composite popularity score.

Purpose:

This method provides the naive baseline. It is not expected to produce the best calendar, but it is essential for comparison.

Expected weakness:

The top thirteen may be visually redundant.

---

## 4.2 Method B: Popularity with Cluster Limits

This method improves the baseline by limiting redundancy.

Selection rule:

1. Rank images by popularity.
2. Select images in descending score order.
3. Skip images from clusters that have already reached their allowed limit.
4. Continue until thirteen images are selected.
5. Assign months using month-fit scores.
6. Choose the most popular selected image as the cover.

Cluster limits may use:

1. Visual clusters.
2. Description clusters.
3. Multimodal clusters.
4. Mission-phase clusters.

Example constraint:

No more than two images from the same dominant visual cluster.

Purpose:

This method keeps the selection simple while avoiding excessive similarity.

---

## 4.3 Method C: Top Images per Cluster

This method treats clusters as review groups.

Selection rule:

1. Build visual, description, or multimodal clusters.
2. Rank images within each cluster.
3. Select the top one or two images from the strongest clusters.
4. Ensure the result contains thirteen images.
5. Assign months using month-fit scores.
6. Choose the highest-popularity selected image as the cover.

Purpose:

This method is useful for displaying collapsible review groups and showing the top few picks from each group.

Expected benefit:

It produces a more balanced slate and makes the selection process easier to explain.

---

## 4.4 Method D: Month-First Selection

This method selects the best image for each month.

Selection rule:

1. Score every image for every month from December 2026 through December 2027.
2. For each month, identify high-fit images.
3. Select one image per month while enforcing diversity constraints.
4. Resolve conflicts where one image is best for multiple months.
5. Choose the most popular selected image as the cover.

Purpose:

This method prioritizes calendar usability rather than general popularity.

Expected benefit:

It avoids assigning strong images to months where they do not fit well.

---

## 4.5 Method E: Multi-Objective Calendar Optimization

This is the preferred advanced method.

Selection rule:

1. Score each image for preference, uncertainty, visual cluster, description cluster, mission phase, month fit, and cover suitability.
2. Generate candidate thirteen-image slates.
3. Assign images to months.
4. Score the whole calendar as a collection.
5. Penalize redundancy.
6. Reward month fit, diversity, popularity, and mission coverage.
7. Choose the best-scoring slate.
8. Choose the most popular image among the selected thirteen as the cover.

Calendar utility should include:

1. Image popularity.
2. Broad voter appeal.
3. Score confidence.
4. Visual diversity.
5. Description diversity.
6. Mission-phase coverage.
7. Month suitability.
8. Cover suitability.
9. Print suitability.
10. Redundancy penalty.
11. Overconcentration penalty.

Purpose:

This method directly optimizes the calendar as a complete product.

---

## 4.6 Method F: Human-Reviewed Data Selection

This method uses data to narrow the field, then allows human review.

Selection rule:

1. Generate several candidate slates using Methods A-E.
2. Display each slate with scores and explanations.
3. Show the strongest alternates for each selected image.
4. Allow reviewer replacement.
5. Require a reason for every manual override.
6. Re-score the final slate.
7. Choose the most popular selected image as the cover unless manually overridden.

Purpose:

This keeps the process data-driven while preserving final aesthetic judgment.

---

# 5. Recommended Selection Workflow

The project should generate at least five candidate calendars:

1. Top popularity baseline.
2. Popularity with cluster limits.
3. Top images per cluster.
4. Month-first selection.
5. Multi-objective optimized calendar.

Each candidate should be scored and compared.

The recommended final workflow:

1. Generate image preference scores.
2. Generate visual clusters.
3. Generate description clusters.
4. Generate multimodal clusters.
5. Generate month-fit scores for all thirteen months.
6. Generate cover-fit scores.
7. Produce candidate slates.
8. Compare candidate slates against baseline.
9. Review top candidates.
10. Select final thirteen images.
11. Assign final months.
12. Select cover from the thirteen selected images.
13. Generate printable calendar pages.

---

# 6. Cover Selection Rule

The cover image must be one of the thirteen selected monthly images.

Default rule:

The cover is the selected image with the highest composite popularity score.

Composite popularity score may combine:

1. Batch selection rate.
2. Elo score.
3. Bradley-Terry-Luce score.
4. Borda/category score.
5. Bayesian preference score.
6. Broad appeal score.
7. Cover suitability score.

Recommended cover formula:

| Component                | Weight |
| ------------------------ | -----: |
| Composite popularity     |    50% |
| Cover suitability        |    30% |
| Broad appeal             |    10% |
| Print/layout suitability |    10% |

Manual override is allowed, but it must be documented.

Override reasons may include:

1. Better typography space.
2. Better symbolic mission value.
3. Better visual impact.
4. Better sales appeal.
5. Avoiding reuse of an image already too dominant in the monthly sequence.

---

# 7. Month Assignment

Each selected image should be assigned to one month from December 2026 through December 2027.

Month assignment should consider:

1. Month-fit score.
2. Mission chronology.
3. Visual flow.
4. Emotional pacing.
5. Color balance.
6. Subject balance.
7. Cluster diversity.
8. Description sentiment.
9. Calendar narrative.
10. Avoiding similar images in adjacent months.

The assignment should be modeled as an optimization problem:

Each selected image must be assigned to exactly one month.

Each month must receive exactly one image.

No image may appear on more than one monthly page.

The cover reuses one of the thirteen images and does not affect month assignment.

---

# 8. Calendar Page Layout

## 8.1 Page Size

All pages should be designed for:

| Property       | Value                          |
| -------------- | ------------------------------ |
| Page size      | 8.5 x 11 inches                |
| Orientation    | Portrait                       |
| Print target   | Standard US Letter             |
| Output formats | PDF, PNG preview, HTML preview |
| Primary use    | Display and print              |

## 8.2 Page Structure

Each monthly page is divided into two main regions:

| Region      |         Page Area | Purpose                       |
| ----------- | ----------------: | ----------------------------- |
| Top half    | Approximately 50% | Image                         |
| Bottom half | Approximately 50% | Calendar grid and description |

The image occupies the top half of the page.

The bottom half contains:

1. Calendar grid.
2. Month title.
3. Small image description at bottom right.

## 8.3 Bottom Half Layout

The description must fit to the right of the calendar and below the image.

The description may take no more than **25% of the bottom half**.

Practical layout:

| Bottom-Half Area              | Approximate Share |
| ----------------------------- | ----------------: |
| Calendar grid and month title |               75% |
| Description block             |       25% maximum |

The description block should be positioned at the bottom right of the lower half.

The calendar grid should remain the dominant element in the bottom half.

---

# 9. Monthly Page Layout Specification

## 9.1 Page Regions

For an 8.5 x 11 portrait page:

| Region              | Approximate Dimensions                  |
| ------------------- | --------------------------------------- |
| Full page           | 8.5 in wide x 11 in tall                |
| Safe margin         | 0.25-0.5 in                             |
| Image region        | Top half, approximately 8.0 x 5.0 in    |
| Bottom region       | Bottom half, approximately 8.0 x 5.0 in |
| Calendar grid       | Lower left and center                   |
| Description block   | Lower right                             |
| Description maximum | 25% of bottom half                      |

## 9.2 Image Region

The image region should:

1. Occupy the top half of the page.
2. Preserve image aspect ratio.
3. Use crop/fill rules appropriate for print.
4. Avoid cropping important subjects.
5. Support full-bleed or safe-margin variants.
6. Include optional small caption or image ID only if desired.
7. Not interfere with the monthly calendar below.

Image placement rules:

| Rule               | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| Fit mode           | Crop-to-fill preferred for final print                               |
| Safe crop          | Face, Moon, Earth, spacecraft, and key subject should remain visible |
| Aspect handling    | Letterbox allowed for images that should not be cropped              |
| Resolution warning | Flag images below print-quality threshold                            |
| Subject warning    | Flag images with key subject near page edge                          |

---

# 10. Calendar Grid Specification

Each monthly page should include:

1. Month name.
2. Year.
3. Days of week.
4. Calendar grid.
5. Dates from prior/next month optionally grayed or omitted.
6. Enough white space for readability.

Calendar grid requirements:

| Requirement            | Description                        |
| ---------------------- | ---------------------------------- |
| Week starts            | Configurable, default Sunday       |
| Month title            | Clearly visible above grid         |
| Date cells             | Large enough for print readability |
| Prior/next month dates | Optional                           |
| Holidays               | Optional later enhancement         |
| Moon phase             | Optional later enhancement         |
| Mission annotations    | Optional later enhancement         |

---

# 11. Description Block Specification

The description block appears at the bottom right of the page.

Requirements:

1. Must fit below the image.
2. Must fit to the right of the calendar.
3. Must not exceed 25% of the bottom-half area.
4. Should contain a concise description.
5. Should include mission context when available.
6. Should not visually dominate the calendar grid.
7. Should use readable font size.
8. Should support automatic truncation or summarization.

Suggested content:

1. Image title.
2. Short description.
3. Mission date/time if useful.
4. Photographer or camera if useful.
5. Distance from Earth/Moon if meaningful.

Description length target:

| Field         |    Suggested Limit |
| ------------- | -----------------: |
| Title         |      60 characters |
| Description   | 250-400 characters |
| Metadata line |      80 characters |

If the source description is too long, generate a short calendar caption.

---

# 12. Cover Page Layout

The cover page uses one of the thirteen selected monthly images.

Cover page should include:

1. Cover image.
2. Calendar title.
3. Year range: December 2026 - December 2027.
4. Optional subtitle.
5. Optional mission/source attribution.
6. Optional small description.

Cover image selection:

1. Must be one of the thirteen selected monthly images.
2. Default is highest composite popularity among the selected thirteen.
3. Cover suitability score may break ties.
4. Human override may be allowed with documented reason.

Cover layout should support:

1. Full-page image.
2. Image with title overlay.
3. Image top with title block below.
4. Safe typography area.
5. Print bleed/safe-margin settings.

---

# 13. Calendar Candidate Data Model Additions

## 13.1 `dim_calendar_month`

**Grain:** one calendar month slot.

| Column                     | Description                       |
| -------------------------- | --------------------------------- |
| `calendar_month_sk`        | Surrogate key                     |
| `calendar_year`            | 2026 or 2027                      |
| `calendar_month_number`    | 1-12                              |
| `calendar_month_label`     | December 2026, January 2027, etc. |
| `calendar_sequence_number` | 1-13                              |
| `start_date`               | First day of month                |
| `end_date`                 | Last day of month                 |
| `days_in_month`            | Number of days                    |
| `week_start_rule`          | Sunday or Monday                  |
| `created_at`               | Create timestamp                  |

## 13.2 `mart_calendar_candidate`

**Grain:** one generated calendar candidate.

| Column                  | Description                                 |
| ----------------------- | ------------------------------------------- |
| `calendar_candidate_sk` | Surrogate key                               |
| `candidate_run_id`      | Optimization run                            |
| `candidate_name`        | Display name                                |
| `calendar_start_month`  | December 2026                               |
| `calendar_end_month`    | December 2027                               |
| `monthly_image_count`   | 13                                          |
| `cover_image_sk`        | One of the thirteen selected monthly images |
| `objective_score`       | Total score                                 |
| `popularity_score`      | Preference component                        |
| `diversity_score`       | Diversity component                         |
| `month_fit_score`       | Month assignment component                  |
| `cover_fit_score`       | Cover component                             |
| `redundancy_penalty`    | Similarity penalty                          |
| `uncertainty_penalty`   | Risk penalty                                |
| `created_at`            | Create timestamp                            |

## 13.3 `mart_calendar_candidate_month_image`

**Grain:** one image assigned to one calendar month.

| Column                              | Description            |
| ----------------------------------- | ---------------------- |
| `calendar_candidate_month_image_sk` | Surrogate key          |
| `calendar_candidate_sk`             | Candidate key          |
| `calendar_month_sk`                 | Month key              |
| `image_sk`                          | Assigned image         |
| `calendar_sequence_number`          | 1-13                   |
| `month_fit_score`                   | Image-month fit        |
| `image_popularity_score`            | Image popularity       |
| `cluster_diversity_score`           | Diversity contribution |
| `description_fit_score`             | Text/month fit         |
| `assignment_reason`                 | Explanation            |
| `created_at`                        | Create timestamp       |

## 13.4 `mart_calendar_cover_selection`

**Grain:** one cover selection per candidate calendar.

| Column                   | Description                              |
| ------------------------ | ---------------------------------------- |
| `cover_selection_sk`     | Surrogate key                            |
| `calendar_candidate_sk`  | Candidate key                            |
| `cover_image_sk`         | Selected cover image                     |
| `cover_selection_method` | popularity, cover_score, manual_override |
| `cover_popularity_score` | Popularity component                     |
| `cover_fit_score`        | Cover suitability                        |
| `typography_space_score` | Layout suitability                       |
| `selection_reason`       | Explanation                              |
| `manual_override_flag`   | True/false                               |
| `manual_override_reason` | Required if overridden                   |
| `created_at`             | Create timestamp                         |

---

# 14. Page Layout Data Model

## 14.1 `calendar_page_layout_template`

**Grain:** one reusable layout template.

| Column                            | Description                                        |
| --------------------------------- | -------------------------------------------------- |
| `layout_template_sk`              | Surrogate key                                      |
| `template_name`                   | Example: letter_portrait_image_top_calendar_bottom |
| `page_width_in`                   | 8.5                                                |
| `page_height_in`                  | 11                                                 |
| `orientation`                     | portrait                                           |
| `margin_top_in`                   | Configurable                                       |
| `margin_bottom_in`                | Configurable                                       |
| `margin_left_in`                  | Configurable                                       |
| `margin_right_in`                 | Configurable                                       |
| `image_region_json`               | Coordinates and dimensions                         |
| `calendar_region_json`            | Coordinates and dimensions                         |
| `description_region_json`         | Coordinates and dimensions                         |
| `description_max_bottom_half_pct` | 25                                                 |
| `created_at`                      | Create timestamp                                   |

## 14.2 `calendar_page_render`

**Grain:** one rendered page output.

| Column                    | Description                   |
| ------------------------- | ----------------------------- |
| `calendar_page_render_sk` | Surrogate key                 |
| `calendar_candidate_sk`   | Candidate key                 |
| `calendar_month_sk`       | Month key, nullable for cover |
| `image_sk`                | Image used                    |
| `page_type`               | cover, month                  |
| `layout_template_sk`      | Layout template               |
| `render_status`           | pending, rendered, failed     |
| `output_pdf_path`         | Page PDF                      |
| `output_png_path`         | Preview image                 |
| `output_html_path`        | HTML preview                  |
| `rendered_at`             | Render timestamp              |
| `validation_status`       | pass, warning, fail           |
| `validation_notes`        | Layout validation notes       |

---

# 15. Page Rendering Requirements

The system should be able to display and print:

1. Cover page.
2. December 2026 page.
3. January 2027 page.
4. February 2027 page.
5. March 2027 page.
6. April 2027 page.
7. May 2027 page.
8. June 2027 page.
9. July 2027 page.
10. August 2027 page.
11. September 2027 page.
12. October 2027 page.
13. November 2027 page.
14. December 2027 page.

Output package:

1. Individual page PNG previews.
2. Individual page PDFs.
3. Combined printable PDF.
4. Optional HTML preview.
5. Optional contact sheet of all pages.

---

# 16. Layout Validation

Each rendered page should be validated.

## 16.1 Image Validation

| Check         | Rule                                                          |
| ------------- | ------------------------------------------------------------- |
| Resolution    | Must meet minimum print threshold                             |
| Aspect ratio  | Must fit template with acceptable crop                        |
| Subject crop  | Key subject should not be cut off                             |
| Brightness    | Should not be too dark for print                              |
| Contrast      | Should remain readable with text overlays if any              |
| Duplicate use | Image appears once monthly; cover may reuse one monthly image |

## 16.2 Calendar Validation

| Check                 | Rule                                  |
| --------------------- | ------------------------------------- |
| Correct month         | Calendar grid matches assigned month  |
| Correct year          | December 2026 through December 2027   |
| Correct day alignment | Dates align with day-of-week          |
| Complete days         | All days in month are shown           |
| Print readability     | Date numbers readable at final size   |
| Region bounds         | Calendar stays inside assigned region |

## 16.3 Description Validation

| Check              | Rule                                                   |
| ------------------ | ------------------------------------------------------ |
| Region limit       | Description block uses no more than 25% of bottom half |
| Text overflow      | No text outside description region                     |
| Font size          | Must remain readable                                   |
| Description length | Long descriptions are shortened                        |
| Metadata fit       | Metadata line does not overflow                        |
| Placement          | Bottom right below image and beside calendar           |

## 16.4 Cover Validation

| Check              | Rule                                    |
| ------------------ | --------------------------------------- |
| Cover image source | Must be one of thirteen monthly images  |
| Title readability  | Title must be readable                  |
| Typography space   | Text does not obscure important subject |
| Print readiness    | Cover image meets quality threshold     |
| Attribution        | Attribution included if required        |

---

# 17. Description Generation

The source description may be too long for the calendar page.

The system should generate a concise calendar caption.

Caption requirements:

1. Accurate.
2. Short.
3. Readable.
4. Non-technical unless technical detail is valuable.
5. Fits the page.
6. Preserves mission context.
7. Avoids speculative claims.
8. Does not exceed layout region.

Caption structure:

1. Short title.
2. One or two sentence description.
3. Optional metadata line.

Example description budget:

| Element  |          Limit |
| -------- | -------------: |
| Title    |  60 characters |
| Body     | 250 characters |
| Metadata |  80 characters |

---

# 18. Selection Report Requirements

Every generated calendar candidate should include:

1. Thirteen selected images.
2. Assigned month for each image.
3. Cover image.
4. Image popularity score.
5. Month-fit score.
6. Cover-fit score.
7. Cluster membership.
8. Redundancy notes.
9. Selection reason.
10. Alternate images considered.
11. Baseline comparison.
12. Layout warnings.

---

# 19. Calendar Preview Requirements

The project should support review views.

## 19.1 Candidate Summary View

Shows:

1. Candidate name.
2. Total score.
3. Thirteen images.
4. Cover image.
5. Month assignments.
6. Cluster coverage.
7. Redundancy warnings.
8. Layout warnings.

## 19.2 Month Page Preview

Shows:

1. Rendered page.
2. Image metadata.
3. Calendar grid.
4. Description.
5. Layout validation status.
6. Alternate image options.

## 19.3 Cover Preview

Shows:

1. Cover image.
2. Title placement.
3. Cover score.
4. Popularity score.
5. Typography warning if needed.
6. Alternate cover candidates from the same thirteen-image set.

## 19.4 Print Package Preview

Shows:

1. Cover.
2. All thirteen monthly pages.
3. Contact sheet.
4. Print validation results.
5. Export button or build command.

---

# 20. Acceptance Criteria

## 20.1 Image Selection Acceptance Criteria

| ID         | Criterion                                                            |
| ---------- | -------------------------------------------------------------------- |
| AC-SEL-001 | System can generate at least five candidate thirteen-image calendars |
| AC-SEL-002 | Each candidate contains exactly thirteen monthly images              |
| AC-SEL-003 | Months run from December 2026 through December 2027                  |
| AC-SEL-004 | Each month has exactly one image                                     |
| AC-SEL-005 | No monthly image is duplicated across months                         |
| AC-SEL-006 | Cover image is one of the thirteen monthly images                    |
| AC-SEL-007 | Cover image is selected by a documented popularity metric            |
| AC-SEL-008 | Candidate calendars are compared to top-popularity baseline          |
| AC-SEL-009 | Cluster diversity is reported                                        |
| AC-SEL-010 | Month-fit score is reported for each page                            |

## 20.2 Layout Acceptance Criteria

| ID         | Criterion                                             |
| ---------- | ----------------------------------------------------- |
| AC-LAY-001 | Every monthly page is 8.5x11 portrait                 |
| AC-LAY-002 | Image appears on top half of page                     |
| AC-LAY-003 | Calendar appears on bottom half of page               |
| AC-LAY-004 | Description appears at bottom right                   |
| AC-LAY-005 | Description uses no more than 25% of bottom half      |
| AC-LAY-006 | Calendar grid remains readable                        |
| AC-LAY-007 | Description text does not overflow                    |
| AC-LAY-008 | Cover page can be rendered                            |
| AC-LAY-009 | All pages can be exported as PNG previews             |
| AC-LAY-010 | All pages can be exported as a combined printable PDF |

---

# 21. Implementation Phases

## 21.1 Phase C1: Calendar Selection Methods

Deliverables:

1. Top-popularity baseline.
2. Popularity with cluster limits.
3. Top images per cluster.
4. Month-first selection.
5. Multi-objective optimization.
6. Candidate comparison report.

Exit criteria:

1. At least five candidate calendars generated.
2. Each candidate has thirteen monthly images.
3. Each candidate has a cover selected from the thirteen.
4. Each candidate has scoring explanations.

## 21.2 Phase C2: Month Assignment

Deliverables:

1. Calendar month dimension.
2. Month-fit scoring.
3. Assignment optimizer.
4. Month assignment report.

Exit criteria:

1. Every selected image assigned to one month.
2. Every month from December 2026 through December 2027 assigned one image.
3. Assignment reasons generated.
4. Adjacent-month redundancy warnings generated.

## 21.3 Phase C3: Cover Selection

Deliverables:

1. Cover scoring.
2. Cover selection table.
3. Cover candidate report.
4. Cover layout validation.

Exit criteria:

1. Cover image selected from thirteen monthly images.
2. Cover selection method documented.
3. Cover can be manually overridden with reason.
4. Cover page renders successfully.

## 21.4 Phase C4: Page Rendering

Deliverables:

1. 8.5x11 portrait layout template.
2. Monthly page renderer.
3. Cover renderer.
4. PNG previews.
5. Individual PDFs.
6. Combined printable PDF.

Exit criteria:

1. Cover page renders.
2. Thirteen monthly pages render.
3. Description block respects 25% bottom-half limit.
4. Calendar grids are correct.
5. Combined PDF prints correctly.

## 21.5 Phase C5: Review Package

Deliverables:

1. Candidate comparison.
2. Full rendered preview.
3. Contact sheet.
4. Selection report.
5. Layout validation report.
6. Final export package.

Exit criteria:

1. Final calendar can be reviewed visually.
2. Final calendar can be printed.
3. Selection logic is documented.
4. Layout issues are flagged.

---

# 22. Lessons Learned Additions

Add these to the lesson registry:

| Lesson | Topic                                                 |
| ------ | ----------------------------------------------------- |
| 026    | Selecting a 13-month calendar slate                   |
| 027    | Why cover selection is different from month selection |
| 028    | Month-fit scoring and assignment                      |
| 029    | Calendar layout constraints for 8.5x11 portrait       |
| 030    | Balancing image, calendar grid, and description text  |
| 031    | Using cluster limits in visual product selection      |
| 032    | Comparing naive top-N to optimized slate selection    |
| 033    | Rendering print-ready data products                   |
| 034    | Designing printable reports from warehouse outputs    |
| 035    | Explaining calendar selection decisions               |

---

# 23. Summary

The calendar contains thirteen monthly pages covering **December 2026 through December 2027**. Each month receives one image. One of those thirteen selected images is reused as the cover image.

The system should support several data-driven ways to select the thirteen images, including naive popularity, popularity with cluster limits, top images per cluster, month-first selection, multi-objective optimization, and human-reviewed data selection.

The printable product uses an **8.5x11 portrait page**. Monthly pages place the image on the top half and the calendar on the bottom half. A short description appears at the bottom right, beside the calendar and below the image, using no more than **25% of the bottom half**.

The final project should produce both the selected calendar and the evidence explaining why those thirteen images form a stronger calendar than simply choosing the top thirteen by popularity.
