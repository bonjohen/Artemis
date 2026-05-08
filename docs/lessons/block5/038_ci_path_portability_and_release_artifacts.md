# Lesson 038: CI Path Portability and Release Artifacts

## The Lesson

When a project develops on Windows but deploys via CI on Linux, hardcoded paths like `D:/artemis/warehouse.duckdb` will fail silently or crash. Every path that differs between dev and CI must be configurable via environment variable. Similarly, large binary dependencies (databases, model weights) should be published as GitHub Release artifacts and downloaded in CI — not committed to the repo or assumed to exist at a fixed location.

## Context

The Artemis Calendar project develops on Windows 11 with data stored at `D:/artemis/`. The static site build runs in GitHub Actions on `ubuntu-latest`. The build script needs a 49 MB DuckDB warehouse to pre-generate API responses as JSON for GitHub Pages.

## What Happened

1. The GitHub Actions workflow hardcoded `D:/artemis/warehouse.duckdb` as the database destination path after downloading from a release artifact. This is a Windows path that doesn't exist on the Ubuntu runner — `gunzip` would write to a nonsensical path or fail.

2. The workflow referenced `warehouse-v1` as a release tag, but no release existed. The `gh release download` command failed with "release not found," and the entire build failed before reaching the static site generation step.

3. The fix required two changes:
   - **Create the release artifact:** `gzip` the 49 MB database (compresses to 24 MB) and publish via `gh release create warehouse-v1 warehouse.duckdb.gz`.
   - **Use env var for the path:** Change the workflow to download to `/tmp/warehouse.duckdb` and set `ARTEMIS_DB_PATH=/tmp/warehouse.duckdb` when running the build script. The app's `config/settings.py` already reads `ARTEMIS_DB_PATH` with a fallback default — the CI just needed to override it.

## Alternatives Considered

- **Commit the database to git:** At 49 MB (24 MB compressed), this bloats the repo permanently via git history. Release artifacts are versioned but don't inflate clone size.
- **Build the database in CI from raw data:** Would require the full pipeline (downloads, feature extraction, ML models) — impractical for a Pages deployment job.
- **Use a GitHub Actions cache:** Caches are ephemeral and branch-scoped. A release artifact is permanent, versioned, and downloadable from any workflow.

## Key Takeaway

The pattern for large binary dependencies in CI is: **publish as a release artifact, download in CI, configure the path via env var.** This keeps the repo lean, makes the dependency version-explicit, and works across any runner OS. Every path in the project that might differ between environments should be configurable — if `settings.py` already has an env var override, the CI workflow just needs to use it.

## Related Lessons

- [Lesson 043: PII Sanitization in Static Exports](../block6/043_pii_sanitization_in_static_exports.md) — hardcoded paths are prevented by CI portability at entry; PII sanitization removes them at exit
