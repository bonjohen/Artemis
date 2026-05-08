"""Read-only DuckDB connection and dependency injection for the web app."""

from __future__ import annotations

import duckdb
from fastapi import FastAPI, Request

from artemis_calendar.config.settings import DB_PATH


def init_db(app: FastAPI) -> None:
    """Open a read-only DuckDB connection and store it on app.state."""
    app.state.db = duckdb.connect(str(DB_PATH), read_only=True)


def close_db(app: FastAPI) -> None:
    """Close the DuckDB connection."""
    if hasattr(app.state, "db") and app.state.db:
        app.state.db.close()


def get_db(request: Request) -> duckdb.DuckDBPyConnection:
    """FastAPI dependency — returns the shared read-only connection."""
    return request.app.state.db
