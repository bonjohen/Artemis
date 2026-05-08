# Lesson 046: Lazy Imports for Deployment Compatibility

## The Lesson

Import heavy dependencies inside the function that uses them, not at module scope. A module-level `import numpy` means every consumer of that module — including lightweight build scripts, CI pipelines, and serverless functions — must have numpy installed, even if they never call the code path that needs it.

## Context

A FastAPI web application serves image browsing, cluster analysis, and calendar selection for a 12,000-image collection. The cluster routes module added a "spotlight" endpoint that uses numpy for greedy max-min diversity selection on CLIP embeddings. The web app also has a static site generator that imports the same FastAPI app to enumerate routes and pre-render API responses as JSON files. This static build runs in a GitHub Actions CI environment that installs only core dependencies (`pip install .[web]`), not the ML extras (`pip install .[ml]`).

## What Happened

1. Added `import numpy as np` at the top of `web/routes/clusters.py` because the new `_compute_spotlight` function used numpy for embedding distance calculations.
2. The local dev server worked fine — numpy was already installed for the ML pipeline.
3. Pushed to GitHub. The CI workflow ran: checkout → install `.[web]` → download warehouse → build static site. The build script imported `create_app()`, which imported all route modules, which imported numpy. Build failed with `ModuleNotFoundError: No module named 'numpy'`.
4. The fix was one line: move `import numpy as np` from module scope into the `_compute_spotlight` function body. The route module now loads without numpy; numpy is only needed when someone actually calls the spotlight endpoint.
5. The static build never calls the spotlight endpoint (it pre-renders paginated cluster listings, not the diversity calculation), so it never hits the import.

## Key Insights

- **Module imports are transitive.** Importing a FastAPI app imports every router. Importing a router imports every dependency of every endpoint in that router. One heavy import in one endpoint breaks every consumer of the app, even consumers that never touch that endpoint.
- **The failure mode is silent until deployment.** On a development machine with all dependencies installed, there's no signal that a module-level import will break CI. The only way to catch this locally is to test in a minimal environment or audit imports against each `[optional-dependencies]` group.
- **Lazy imports have negligible runtime cost.** Python caches imported modules in `sys.modules`. The first call to a function with a lazy import pays a one-time lookup cost (microseconds). Subsequent calls find the module already cached. The performance argument for module-level imports doesn't apply after the first invocation.
- **The boundary is the dependency group, not the module.** The question isn't "does this file use numpy?" but "does every deployment target that loads this file have numpy?" If the answer is no for any target, the import must be lazy.
- **Framework app factories amplify the problem.** FastAPI, Django, and Flask all import route modules eagerly at app creation time. A single heavy import in any route module becomes a hard dependency of the entire application, including management commands, build scripts, and health checks.

## Applicability

This pattern applies whenever:
- A module has optional heavy dependencies (ML libraries, database drivers, cloud SDKs)
- The module is imported by consumers with different dependency sets (web server, CLI, CI, tests)
- The heavy dependency is used by a subset of the module's functions

Does NOT apply when:
- The dependency is a hard requirement of every consumer (e.g., `fastapi` in a FastAPI routes module)
- Import-time validation is needed (e.g., checking that a required library version is compatible)
- The module is small and single-purpose, so importing it implies needing all its dependencies

## Related Lessons

- [Lesson 038: CI Path Portability](../block5/038_ci_path_portability_and_release_artifacts.md) — another CI-vs-dev environment mismatch: hardcoded paths break CI, heavy imports break CI
- [Lesson 036: Linter Rules vs. Framework Idioms](../block5/036_linter_rules_vs_framework_idioms.md) — linters may flag lazy imports as style violations; suppress per-line rather than restructuring
- [Lesson 047: CLIP Zero-Shot as a Database Column Factory](047_clip_zero_shot_as_database_column_factory.md) — the CLIP tagger that caused the numpy import failure; its numpy dependency must be lazy for CI compatibility
