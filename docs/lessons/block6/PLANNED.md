# Lessons Planned

Future lessons identified from the Claude Code usage insights analysis (64 sessions, 150 commits, May 2026). These are patterns observed but not yet written up as formal lessons.

## Ready to Write (clear pattern, sufficient evidence)

### 058: Test-First Autonomous Phase Execution
**Source:** Insights "On the Horizon" — test-driven autonomous development
**Core teaching:** Write failing tests FIRST for each phase, then iterate autonomously until green. Prevents the cascade of buggy code (59 friction incidents) by catching regressions at the moment of introduction rather than after multiple changes.
**Evidence:** 59 buggy_code friction events across 64 sessions; majority would have been caught by running tests after each file change instead of batching.

### 059: Parallel Sub-Agent Fan-Out with File Ownership
**Source:** Insights "On the Horizon" — parallel sub-agents with conflict guards
**Core teaching:** When spawning multiple sub-agents, assign each an explicit file ownership set with zero overlap. Merge at the parent level. Avoids DB locks, token exhaustion, and edit conflicts seen in 273 agent invocations.
**Evidence:** Agent coordination failures (stuck in plan mode, DB lock conflicts, token exhaustion) across multiple sessions.

### 060: Pre-Flight Checklists for Development Sessions
**Source:** Insights "Self-Healing Infrastructure" + friction analysis
**Core teaching:** Run an automated checklist at session start: kill orphan processes, verify ports, validate dependencies, test DB access, establish test baseline. Turns reactive debugging into proactive validation.
**Evidence:** Port conflicts and DB locks were recurring in nearly every session that involved a dev server.

### 061: Schema-Aware Code Generation
**Source:** Insights friction — "wrong column names" was the top buggy_code pattern
**Core teaching:** Before generating SQL or ORM code, read the actual schema (information_schema.columns or migration files). Never assume column names from memory or conversation context. The schema is the source of truth.
**Evidence:** DuckDB queries using wrong column names (vote_pool vs vote_pool_flag, skipped_flag) required multiple fix rounds.

## Needs More Evidence (pattern emerging, not yet fully formed)

### Explicit Planning Gates Between Exploration and Implementation
**Signal:** 20 "wrong approach" friction events where Claude jumped to implementation before confirming the approach.
**When to write:** After implementing the "planning gates" pattern in 2-3 more projects and measuring whether it reduces wrong-approach incidents.

### Skills as Workflow Compression
**Signal:** The `/phase`, `/lessons`, `/push` skills each compress a multi-step workflow into a single command. The pattern of identifying a repeated workflow → encoding it as a skill → using it is itself a lesson.
**When to write:** After 3+ skills are in active use and the time savings can be quantified.

### Commit Message Archaeology for Lesson Discovery
**Signal:** The `/lessons discover` mode scans git log for lesson candidates. The commit message style (conventional commits with scope) makes this possible. Projects with vague commit messages can't be mined for lessons.
**When to write:** After running discover across 3+ projects and comparing yield by commit message quality.

### Context Window Management as a First-Class Concern
**Signal:** Compact-at-65% rule, compact instructions, focus phrases for manual compaction. The context window is a finite resource that must be managed like memory or disk — it's not infinite and lost context is unrecoverable.
**When to write:** After documenting the specific costs of late compaction (lost corrections, repeated mistakes, context-dependent bugs).
