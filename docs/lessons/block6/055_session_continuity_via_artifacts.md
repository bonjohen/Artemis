# Lesson 055: Session Continuity via Documentation Artifacts

## The Lesson

When working across multiple AI-assisted sessions, continuity must be encoded in files, not in conversation history. A startup document, a plan file with status tracking, and a project CLAUDE.md that reflects current state eliminate ramp-up overhead and prevent context loss from session clears and context compaction.

## Context

A developer working across 64 sessions on 5+ projects needed seamless session handoffs. Each session started with full context loss — no memory of previous conversations. Early sessions wasted 10-15 minutes re-establishing context: "we were working on Phase 7, the tests pass, here's what's left." Later sessions solved this by maintaining durable artifacts that any session could read to immediately understand the project state.

## What Happened

1. Initially relied on conversation history and memory to track state. This failed when sessions were cleared, context was compacted, or the developer switched between projects. Re-explaining the current phase, what had been tried, and what was blocking cost significant time.

2. Introduced three artifact types:
   - **CLAUDE.md** — project-level context: architecture, conventions, data model, current status. Read by every session automatically.
   - **Startup/memory files** — session-specific state: current branch, ahead/behind status, active plan file, phase in progress, unresolved decisions. Updated at session end.
   - **Plan files** — work tracking: phase rows with Open/Started/Completed status and PST timestamps. The plan IS the progress record.

3. Added a discipline: after completing a phase or major task, always update the startup doc before ending the session. This was initially manual ("please update STARTUP.md") but became part of the workflow (the `/phase` skill updates the plan file automatically).

4. Measured the impact: sessions with current artifacts ramped up in under 1 minute (read CLAUDE.md + startup → know exactly where to continue). Sessions without artifacts took 5-15 minutes of "let me read the git log and figure out what we were doing."

5. Context compaction — where the AI summarizes earlier conversation to free space — was the biggest threat to continuity. Compact instructions in CLAUDE.md specify what must survive compaction verbatim: branch name, plan file path, current phase, open questions, user corrections, exact file paths. Without these, compaction would genericize critical details ("we did some work" instead of "Phase 7 row 7.3 is Started, commit pending").

## Key Insights

- **Files outlive conversations.** Conversation history is ephemeral — it's compacted, cleared, and lost between sessions. Files persist. Every piece of information needed to resume work should live in a file, not in a message.
- **Three layers of context serve different needs.** CLAUDE.md is stable (updated monthly), startup docs are volatile (updated per session), plan files are detailed (updated per task row). Each has a different update frequency and audience.
- **Compact instructions are load-bearing.** Without explicit instructions telling the compaction model what to preserve verbatim (branch names, file paths, phase numbers), compaction destroys the precise details needed for session continuity. Generic summaries are useless for execution.
- **Update artifacts BEFORE ending, not after resuming.** Writing the startup doc at session end takes 30 seconds. Reconstructing it at session start takes 5-15 minutes. The asymmetry makes end-of-session updates the obvious choice, yet they're the first thing skipped under time pressure.
- **The CLAUDE.md is a contract, not documentation.** It tells the AI how to behave, what conventions to follow, and what the current state is. Inaccurate CLAUDE.md → wrong assumptions → wrong code. Keeping it current is as important as keeping tests green.

## Applicability

This pattern applies to any multi-session workflow with an AI coding assistant:
- Projects spanning days or weeks with session gaps
- Multi-developer projects where context handoff matters
- Projects where context compaction is expected (long sessions, large codebases)

Does NOT apply when:
- Work is completed in a single session
- The project is small enough that reading the entire codebase takes less time than reading a status doc
- The AI assistant has persistent memory that survives sessions (check your tool's memory model)

## Related Lessons

- [Lesson 054: Phased Autonomous Execution](054_phased_autonomous_execution.md) — the plan file is the primary continuity artifact for phased work
- [Lesson 053: Audit-First Design](053_audit_first_design.md) — the audit doc is another continuity artifact that preserves codebase understanding
