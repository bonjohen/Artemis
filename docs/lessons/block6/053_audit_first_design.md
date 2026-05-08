# Lesson 053: Audit-First Design

## The Lesson

Before writing any code for a new feature, produce a written audit of the existing codebase: what exists, what can be reused, where new code slots in. The audit document prevents reimplementing existing functionality and identifies the exact extension points — saving more time than it costs to write.

## Context

A data science platform with 15+ modules, 168 tests, and 29 database tables needed a major extension: biased voting blocks, vision-language model tagging, block-aware statistics, and static site integration. The extension touched nearly every layer of the stack — synthetic data generation, feature extraction, statistical modeling, validation, web API, and frontend. Without an audit, the risk was high: reimplementing query patterns that already existed, creating parallel data paths that diverged from existing conventions, or missing reusable infrastructure buried in modules the developer hadn't recently touched.

## What Happened

1. Created a formal audit document (`docs/artemis_bias_extension_audit.md`) as the first commit of the project — before any code changes. The audit covered:
   - `synthetic/` — existing voter profiles, vote generation, run metadata, extension points
   - `features/` — visual features, CLIP embeddings, text features, how to add new extractors
   - `models/` — Elo, Borda, Beta-Binomial, composite scoring, where block-aware variants slot in
   - `validate/` — bias detection, calendar validation, extension points for block-level bias
   - `static/` — JSON export, stats page, how new sections integrate
   - `web/` — API routes, frontend architecture, CLI command registration

2. The audit identified three cases where existing code could be reused directly:
   - The `observe/run_manifest.py` run tracking system — no need to build a new one for block vote runs
   - The PyArrow bulk insert pattern from `features/embeddings.py` — reusable for attribute batch writes
   - The `config/sql_helpers.py` run-resolution subqueries — reusable for block statistics queries

3. The audit identified two patterns that needed deliberate deviation:
   - Vote generation used `executemany` for small batches but the block generator would produce 50K+ ballot-image rows. The audit flagged this and led to using PyArrow bulk insert instead (preventing the hanging bug from Lesson 020).
   - The existing bias detection in `validate/` used chi-squared tests on position bias. Block-aware bias detection needed lift-based metrics — a different statistical approach. The audit clarified this wasn't a case of "extend the existing function" but "add a parallel analysis module."

4. The audit took 15 minutes to write. The subsequent 10 implementation phases (vision tagging, voting blocks, statistics, export, web integration, acceptance tests) completed without any "oh, this already exists" rework moments. Three developers reviewing the code confirmed they found no dead code or reimplemented functionality.

## Key Insights

- **An audit is cheaper than rework.** Fifteen minutes reading code and writing notes prevents hours of implementing something that already exists, debugging conflicts with existing patterns, or refactoring to match conventions discovered too late.
- **Audit the extension points, not just the modules.** Knowing "the scoring pipeline exists" isn't enough. The audit should document "new scoring methods slot in by adding a function to `models/` and calling it from `compute_preference_scores()` in `__init__.py`." The extension point is the actionable output.
- **The audit document is a communication artifact.** It's useful beyond the author: reviewers can check the audit against the implementation to verify that reuse claims are accurate, and future developers can read it to understand why certain design decisions were made.
- **Audit scope should match extension scope.** Auditing the entire codebase for a one-file change is waste. Auditing only the module you're changing for a cross-cutting feature is insufficient. The right scope is: every module the new feature will import from, write to, or pattern-match against.
- **The audit commit should contain no code changes.** Mixing audit findings with implementation in the same commit makes it impossible to verify that the audit was done *before* the implementation influenced the findings. A clean audit commit is a checkpoint: "here's what I knew before I started writing code."

## Applicability

Audit-first design is valuable when:
- The codebase has 5+ modules and you're adding a cross-cutting feature
- You're working in a codebase you didn't write or haven't touched recently
- The extension involves multiple integration points (not just "add a new endpoint")
- Multiple developers will review or extend the work

Does NOT apply when:
- The change is isolated to one file or function (the "audit" is just reading that file)
- You wrote the entire codebase recently and have full mental context
- The feature is greenfield with no existing code to integrate with
- The project is small enough that reading every file takes less time than writing an audit document

## Related Lessons

- [Lesson 044: Acceptance Tests as Executable Specifications](044_acceptance_tests_as_executable_specifications.md) — the audit identifies what to test; acceptance tests verify the integration points the audit mapped
- [Lesson 011: Synthetic Data Before Real Data](../block1/synthetic_data_before_real_data.md) — the audit identified that the existing synthetic generator was the right foundation for block vote generation
