# Lesson 056: Environment Self-Interference in AI-Assisted Development

## The Lesson

An AI coding assistant that launches background processes (dev servers, database connections, build watchers) will fight with its own previous instances over shared resources like ports and file locks. Explicit cleanup before each launch — kill orphan processes, release locks, verify port availability — must be part of the workflow, not an afterthought.

## Context

Across 64 development sessions, port conflicts and database locks were a recurring friction source. The AI assistant would launch a dev server on port 8070, then later need to restart it (after code changes), but fail to kill the previous instance. The result: "port already in use" errors, DuckDB "file already open" errors, and cascading failures that wasted 5-10 minutes per incident. The root cause was always the same: the AI's own previous process was still running.

## What Happened

1. A typical incident: the dev server is running on port 8070. The user asks for a code change. The AI edits the file and tries to restart the server. The old process is still listening on 8070. The new process fails with "address already in use." The AI tries again. Same error. Eventually someone thinks to kill the old process.

2. DuckDB has a single-writer constraint — only one process can open the database for writing. The web server opens it read-only, but if a CLI process (tagging, deduplication) has the database open for writing, the web server can't start. And if a previous CLI process crashed without closing the connection, the lock persists until the process is killed.

3. The fix was straightforward but required discipline: before every server launch, check for and kill existing processes on the target port. Before every database write operation, verify no other process holds the lock. This was codified into the `/push` skill and into CLAUDE.md as a development server rule.

4. The pattern repeated across projects — not just Artemis. Any project with a dev server hit the same issue. The fix was the same each time, confirming it's a systemic pattern rather than a project-specific bug.

## Key Insights

- **AI assistants don't track their own background processes.** When an AI launches a process in the background, it may lose track of it across conversation turns, context compactions, or session restarts. The process outlives the context that created it.
- **Pre-launch cleanup is cheaper than post-failure debugging.** Running `kill $(lsof -ti:8070)` before launching a server takes milliseconds. Debugging "address already in use" after the fact takes minutes and interrupts the user's flow.
- **Embedded databases amplify the problem.** Server databases (PostgreSQL, MySQL) have their own process management. Embedded databases (SQLite, DuckDB) use file locks that persist until the process exits. A crashed or abandoned process holds the lock indefinitely.
- **Codify the cleanup in reusable patterns.** Adding cleanup to CLAUDE.md rules, skill definitions, or hooks ensures it happens every time without the developer remembering to ask for it. The `/push` skill's pre-flight check is an example.
- **Background tasks should be auditable.** When launching a process in the background, log the PID and the purpose. When restarting, check for processes matching that purpose. "Kill everything on port 8070" is a blunt instrument but effective; "kill process 12345 that we launched for the dev server" is better but requires tracking state.

## Applicability

This pattern applies whenever an AI assistant manages long-running processes:
- Dev servers (FastAPI, Express, Django)
- Database connections (embedded DBs, connection pools)
- Build watchers (webpack, tsc --watch)
- Background tasks (data processing, model inference)

Does NOT apply when:
- All operations are synchronous and short-lived
- Process management is handled by a container orchestrator (Docker, K8s)
- The development environment has built-in process supervision (some IDEs manage this)

## Related Lessons

- [Lesson 031: Read-Only DB for Web Layers](../block5/031_read_only_db_for_web_layers.md) — the web server opens DuckDB read-only specifically to avoid writer lock conflicts with the CLI
- [Lesson 046: Lazy Imports for Deployment Compatibility](046_lazy_imports_for_deployment_compatibility.md) — another environment mismatch pattern, but at import time rather than runtime
