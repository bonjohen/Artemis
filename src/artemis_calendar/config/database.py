"""Database connection and schema migration management."""

from pathlib import Path

import duckdb

from artemis_calendar.config.settings import DB_PATH, MIGRATIONS_DIR


def get_connection(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection, creating parent directories if needed."""
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def _ensure_migration_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version  INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def get_applied_versions(conn: duckdb.DuckDBPyConnection) -> set[int]:
    _ensure_migration_table(conn)
    rows = conn.execute("SELECT version FROM _migrations").fetchall()
    return {r[0] for r in rows}


def apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_dir: Path | None = None) -> list[str]:
    """Apply all pending SQL migrations in order. Returns list of applied filenames."""
    mdir = migrations_dir or MIGRATIONS_DIR
    if not mdir.exists():
        return []

    _ensure_migration_table(conn)
    applied = get_applied_versions(conn)

    migration_files = sorted(mdir.glob("*.sql"))
    newly_applied = []

    for mf in migration_files:
        version = int(mf.name.split("_")[0])
        if version in applied:
            continue
        sql = mf.read_text(encoding="utf-8")
        conn.execute(sql)
        conn.execute(
            "INSERT INTO _migrations (version, filename) VALUES (?, ?)",
            [version, mf.name],
        )
        newly_applied.append(mf.name)

    return newly_applied
