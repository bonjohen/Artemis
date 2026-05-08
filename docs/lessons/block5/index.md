# Block 5: Web App & Interactive Tooling Lessons

6 lessons from the web app implementation (FastAPI + vanilla JS SPA for interactive calendar selection).

| # | Lesson | Core Teaching |
|---|---|---|
| 031 | [Read-Only DB Connections for Web Layers](031_read_only_db_for_web_layers.md) | Open the warehouse read-only in the web tier so the pipeline CLI can still write |
| 032 | [Startup Cache for Interactive Scoring](032_startup_cache_for_interactive_scoring.md) | Pre-load scoring dicts into memory at startup; query the DB per-request only for browse/search |
| 033 | [Vanilla JS SPA Without a Build Step](033_vanilla_js_spa_no_build_step.md) | Hash routing + dynamic import() delivers a functional SPA with zero toolchain overhead |
| 034 | [Reusing Query Modules Across CLI and Web](034_reusing_query_modules_across_layers.md) | Import query functions directly; wrap with Pydantic at the API boundary, not in the query layer |
| 035 | [Design System Portability via Tokens](035_design_system_portability_via_tokens.md) | CSS custom properties as a shared asset make visual consistency free across standalone tools |
| 036 | [Linter Rules vs. Framework Idioms](036_linter_rules_vs_framework_idioms.md) | When a linter rule conflicts with a framework's official pattern, suppress per-line — don't restructure |
