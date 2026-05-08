# Lesson 054: Phased Autonomous Execution Plans

## The Lesson

Breaking large projects into numbered, independently shippable phases — each with explicit entry criteria, exit criteria, and a commit checkpoint — transforms ambitious multi-session work from a coordination problem into a queue of self-contained tasks. The plan file is both the work instruction and the progress tracker.

## Context

Over 64 Claude Code sessions spanning one month, a developer completed 150 commits across five major projects: a Telegram RPG bot (20 phases), an image selection pipeline (11 phases), a certification quiz site (multi-file redesigns), and more. The consistent pattern: write a phased plan, execute sequentially with commits at each milestone, and track progress in the plan file itself. This pattern powered deliverables that would otherwise require careful coordination across many sessions.

## What Happened

1. Early sessions used ad-hoc instructions: "build X, then Y, then Z." This worked for small tasks but failed for multi-day projects. Context was lost between sessions, work was duplicated, and it was unclear what had been done vs. what remained.

2. Adopted a structured plan format: numbered phases, each with a goal, dependencies, task rows (status, timestamps), and a summary block. The plan file lives in `docs/` and is committed alongside the code.

3. Each phase follows a strict cycle: mark rows as Started → do the work → run tests → mark as Completed → write Phase Summary → commit. The commit message references the phase number and scope.

4. When a session ends mid-plan, the plan file itself records exactly where work stopped. The next session reads the plan, finds the first Open row, and continues. No verbal handoff needed — the artifact is the handoff.

5. Over 150 commits, this pattern produced zero cases of "what was I working on?" confusion. Rollback was always possible to the last phase commit. Reviewers could trace the commit history against the plan phases 1:1.

6. The pattern scaled from 3-phase plans (simple feature additions) to 20-phase plans (full RPG bot implementation) without modification. The overhead of writing the plan (15-30 minutes) was recovered many times over by eliminating coordination friction.

## Key Insights

- **The plan file is the single source of truth for progress.** Not conversation history, not memory, not git log — the plan file with its Started/Completed timestamps is the authoritative record of what's done and what remains. This survives session clears, context compaction, and even developer handoffs.
- **One commit per phase, never partial.** Committing mid-phase creates rollback ambiguity — "is this commit safe to deploy?" With one commit per completed phase, every commit represents a verified, tested, independently meaningful state.
- **Phase dependencies prevent ordering mistakes.** Each phase declares what it depends on ("Depends on: Phase 3"). This makes parallelization opportunities visible and prevents starting work that requires unfinished prerequisites.
- **The overhead is fixed, the savings scale with complexity.** Writing a plan takes the same effort for a 5-phase and a 20-phase project. But the coordination savings grow linearly with phase count and superlinearly with session count. A 20-phase project spanning 5 sessions would be nearly impossible without the plan.
- **Tests gate commits, not phases.** "Run all tests and fix until green" is the commit criterion, not "all phase tasks done." A phase with passing tests but one cosmetic TODO is committable. A phase with all tasks done but failing tests is not.

## Applicability

This pattern applies to any multi-step implementation where:
- Work spans multiple sessions or days
- Multiple components must be coordinated
- Rollback to a known-good state must be possible
- Progress must be visible to others (or to your future self)

Does NOT apply when:
- The task is a single atomic change (one file, one function)
- Exploration is needed before planning (do a design phase first)
- Requirements are changing faster than phases can be completed

## Related Lessons

- [Lesson 053: Audit-First Design](053_audit_first_design.md) — the audit is Stage 1; the phased plan is Stage 3 of the same five-stage workflow
- [Lesson 044: Acceptance Tests as Executable Specifications](044_acceptance_tests_as_executable_specifications.md) — tests gate phase commits; the test suite is the executable specification for "is this phase done?"
