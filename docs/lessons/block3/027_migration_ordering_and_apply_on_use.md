# Lesson 027: Migration Ordering and Apply-on-Use Gaps

## The Lesson

When a database migration creates a table that new code writes to, the migration must be applied before the code runs — not just before the next CLI invocation. If the code path that triggers the write doesn't call `apply_migrations()`, the table won't exist at runtime, even though the migration file is on disk and other commands apply it correctly.

## Context

A DuckDB-based data warehouse used numbered SQL migration files (001–007) applied by an `apply_migrations()` function that reads the `_migrations` table, finds unapplied files, and executes them in order. Each CLI command called `apply_migrations(conn)` at startup. Migration 006 created two scoring mart tables. Migration 007 created two calendar optimization tables. Both migrations existed on disk but had to be applied via code.

## What Happened

1. Added migration 006 (`006_create_scoring_tables.sql`) to create `mart_image_preference_score` and `mart_inter_rater_reliability`. The CLI's `compute-scores` command called `apply_migrations(conn)` at the top, so the tables would be created on first run.
2. Ran `compute-scores` — it completed silently with no output. Queried the table — `Table with name mart_image_preference_score does not exist`. The migration hadn't been applied.
3. Investigated: the `_migrations` table showed versions 1–5 applied, but not 6. The `migrate` command also showed "no pending migrations" — which was wrong.
4. Root cause: the `migrate` CLI command worked correctly, but `compute-scores` had a separate connection path that didn't properly trigger migration 006. Running `migrate` explicitly, then `compute-scores`, worked.
5. The same pattern recurred with migration 007 for calendar tables. The `optimize` command called `apply_migrations(conn)` but the migration still wasn't applied on the first run.
6. The fix was to ensure `apply_migrations()` was called and its result verified before any write operation that depends on new tables. Additionally, running `migrate` as a standalone step before any new pipeline stage became standard practice.

## Key Insights

- **"Migration file exists" ≠ "migration is applied."** A migration on disk does nothing until code reads and executes it. If the code path that triggers the write doesn't apply migrations, the table doesn't exist — regardless of what's on disk.

- **Test the full write path, not just the migration.** Running `migrate` and seeing "006 applied" doesn't prove that `compute-scores` will find the table. The scoring command has its own connection lifecycle; test through the actual command.

- **Silent failures are worse than crashes.** A CLI command that completes with no output and no error — but also no data written — is the hardest failure mode to debug. Add verification queries after critical writes: `SELECT count(*) FROM table` to confirm rows landed.

- **Make migration application idempotent and visible.** `CREATE TABLE IF NOT EXISTS` prevents crashes on re-run. Logging which migrations were applied (and returning the list) makes it visible whether anything happened.

- **Standalone `migrate` before new pipeline stages.** When adding a new migration, run `migrate` explicitly and verify before running the pipeline that depends on it. Don't rely on the pipeline's internal `apply_migrations()` call for the first run.

## Applicability

This applies to any system with schema migrations (Django, Alembic, Flyway, Knex, custom):
- Adding a new table that a new feature writes to
- Adding columns that new code reads from
- Any deployment where "run migrations" is a separate step from "deploy code"

The pattern is especially treacherous in embedded databases (SQLite, DuckDB) where there's no separate database server with its own migration lifecycle — migrations only run when application code triggers them.

## Related Lessons

- [Lesson 040: Controlled Vocabulary as Schema Contract](../block6/040_controlled_vocabulary_as_schema_contract.md) — migration 009 creates tables that align with the attribute vocabulary; the vocabulary validates at load time what the migration enforces at schema time
