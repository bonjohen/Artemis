# Lesson 059: Derive Metrics from Immutable Fact Tables, Not Mutable State

## The Lesson

When a dashboard metric can be computed either from a mutable state flag or from an immutable record table, always derive it from the immutable source. Mutable flags reflect the *current* state, which may not be the state your metric is trying to describe. Immutable fact tables preserve the *historical* truth regardless of downstream operations.

## Context

A web app displayed deduplication statistics for a 12,217-image collection. The pipeline had identified 450 duplicate groups containing 10,504 member images (10,054 near-duplicates + 450 masters). The dedup process sets an `is_suppressed` flag on duplicate images in the dimension table, but also stores group membership in a separate `dedup_image_member` fact table that records every member and its similarity to the group master.

## What Happened

1. The curation page needed to display "Near-Duplicates Found" as a headline stat. The initial implementation computed this as `total_images - active_images`, where "active" meant images with `is_suppressed = false` in the mutable `dim_image` table.

2. During development, `restore_all()` had been called to un-suppress all images for testing. This set every `is_suppressed` flag back to `false`, making `total - active = 0`.

3. The page showed "0 Near-Duplicates" — factually wrong. The dedup analysis had found 10,054 duplicates; the suppression flags just happened to be cleared.

4. The fix was to query `dedup_image_member` instead: `total_members - group_count = 10,504 - 450 = 10,054`. This table is append-only — its rows record the dedup analysis results regardless of whether suppression has been applied, reversed, or re-run.

5. The API was updated to return both `total_members` and `duplicates` as first-class fields derived from the immutable table, rather than computing them from the mutable flag.

## Key Insights

- **Mutable flags answer "what is true now"; fact tables answer "what was found."** A dashboard that reports analysis results should read from the analysis output (fact table), not from the operational state that may have been modified since the analysis ran. The `is_suppressed` flag is an operational control; `dedup_image_member` is the analytical record.

- **`total - active` is a derived metric with hidden dependencies.** It looks simple, but it couples the displayed stat to every operation that can change `is_suppressed` — not just dedup, but also manual overrides, restore operations, and re-runs. The fact-table query has no such coupling.

- **Test with state mutations, not just the happy path.** The bug was invisible when suppression was active. It only surfaced after `restore_all()` cleared the flags. Any metric derived from mutable state should be tested after the state has been toggled back and forth.

- **Name the metric's source in the API contract.** Returning a field called `duplicates` that is silently computed from `total - active` invites the same confusion downstream. When the API explicitly exposes `total_members` (from the fact table) and `duplicates` (computed as `total_members - groups`), consumers can see where the number comes from and can't accidentally recompute it from the wrong source.

## Applicability

This applies to any system where analytical results are applied via mutable flags: feature flags, soft deletes, approval workflows, A/B test assignments. The general rule: if the metric describes "what the analysis found," read from the analysis output table. If the metric describes "what is currently active," read from the flag. The bug happens when you conflate the two.

## Related Lessons

- [Connected Components for Transitive Dedup](../block6/050_connected_components_for_transitive_dedup.md) — the dedup analysis that produces the immutable fact table this lesson depends on
- [DuckDB Cursor-Per-Request](058_duckdb_cursor_per_request.md) — another bug surfaced on the same curation page, from the same set of API endpoints

## Metadata

- **Category:** eng
- **Block:** block7
- **Tags:** metrics, data-modeling, mutable-state, fact-tables, dashboards
