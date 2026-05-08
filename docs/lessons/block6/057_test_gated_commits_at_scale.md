# Lesson 057: Test-Gated Commits at Scale

## The Lesson

Gate every commit on a passing test suite, not on "the feature looks done." With 1,500+ tests across a project, the suite catches regressions that visual inspection misses — wrong column names, broken imports, type mismatches, off-by-one errors. The test suite is the contract for "this commit is safe," and the discipline of never committing red tests prevents cascading failures across phases.

## Context

A multi-project development workflow maintained test suites ranging from 131 tests (data validation) to 1,500+ tests (RPG bot) to 5,101 assertions (render equivalence). The developer's rule: never commit unless all tests pass. This discipline was tested repeatedly — buggy generated code was the single largest friction source (59 incidents across 64 sessions), but gating commits on green tests prevented most bugs from persisting past the commit that introduced them.

## What Happened

1. The most common bug pattern: generated code used wrong column names, incorrect regex, or type mismatches. These bugs were syntactically valid — no import errors, no crashes — but produced wrong results. Without tests, they would have been committed and discovered much later.

2. The commit workflow: implement the change → run `pytest` → if red, fix and re-run → when green, commit. This added 1-3 minutes per commit (test suite runtime) but saved hours of debugging later. A bug caught at commit time takes seconds to fix; the same bug found 5 commits later requires git bisect and careful untangling.

3. Equivalence testing was particularly valuable during migrations. When converting XML exam data to JSON, 5,101 individual assertions verified that every question, answer, hint, and metadata field survived the conversion identically. This caught encoding issues (HTML entities, whitespace normalization) that would have been invisible to manual inspection.

4. The test suite grew alongside the codebase: 168 tests at Phase S3-S4, 259 tests after adding voting blocks and acceptance tests. Each new module added its own test file. The discipline was: if you add a module, you add tests for it. No exceptions.

5. One key insight: running tests *before* making changes (baseline) and *after* each file change (incremental) caught regressions immediately. The alternative — making many changes then running tests — produced compound failures where multiple bugs interacted and root causes were ambiguous.

## Key Insights

- **Test-gated commits prevent bug propagation.** A bug committed in Phase 3 that's caught in Phase 7 requires understanding both phases to fix. A bug caught before the Phase 3 commit is fixed in the context where it was introduced — trivially.
- **Large test suites are fast enough for commit-gating.** 259 tests in 173 seconds. 1,500 tests in under 5 minutes. The latency is real but small compared to the cost of debugging a committed regression.
- **Run tests incrementally, not just at commit time.** After each file change, run the relevant tests immediately. This catches the bug while the change is fresh in context. Batching changes and then testing produces compound failures.
- **Equivalence tests catch what unit tests miss.** Unit tests verify behavior ("does this function return the right thing?"). Equivalence tests verify preservation ("is the output identical to the reference?"). Both are needed — equivalence tests are especially valuable during migrations, refactors, and format conversions.
- **The test suite is a living specification.** When tests pass, the system conforms to its specification. When a new feature is added, new tests extend the specification. The test file is often the best documentation of what a module actually does.

## Applicability

Test-gated commits work for any project with:
- An automated test suite (unit, integration, or end-to-end)
- A commit workflow (not continuous auto-save)
- Multiple developers or AI-assisted development (where generated code may have subtle bugs)

Does NOT apply when:
- No test suite exists yet (write tests first — see Lesson 044)
- Tests are flaky (fix the tests before gating on them)
- The test suite takes so long that gating would block development (optimize the suite or gate on a subset)

## Related Lessons

- [Lesson 044: Acceptance Tests as Executable Specifications](044_acceptance_tests_as_executable_specifications.md) — acceptance tests are the most valuable tests for gating: they verify end-to-end behavior, not just unit correctness
- [Lesson 054: Phased Autonomous Execution](054_phased_autonomous_execution.md) — test-gated commits are the commit criterion for each phase in the execution cycle
