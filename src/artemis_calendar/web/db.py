"""Read-only DuckDB connection and dependency injection for the web app."""

from __future__ import annotations

import logging

import duckdb
from fastapi import FastAPI, Request

from artemis_calendar.config.settings import DB_PATH
from artemis_calendar.config.sql_helpers import LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN

logger = logging.getLogger("artemis.web.db")


def init_db(app: FastAPI) -> None:
    """Open a read-only DuckDB connection, store it, and load caches."""
    app.state.db = duckdb.connect(str(DB_PATH), read_only=True)
    _load_cache(app)


def close_db(app: FastAPI) -> None:
    """Close the DuckDB connection."""
    if hasattr(app.state, "db") and app.state.db:
        app.state.db.close()


def get_db(request: Request) -> duckdb.DuckDBPyConnection:
    """FastAPI dependency — returns a per-request cursor.

    DuckDB's Python driver does not support concurrent queries on a single
    connection object from multiple threads.  Creating a cursor for each
    request lets uvicorn's thread-pool serve parallel reads safely.
    """
    return request.app.state.db.cursor()


def _load_cache(app: FastAPI) -> None:
    """Load scoring dicts into app.state for interactive selection scoring."""
    conn = app.state.db

    # Preference scores
    try:
        rows = conn.execute(
            f"""
            SELECT image_sk, posterior_mean
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
            """
        ).fetchall()
        app.state.preference = {int(r[0]): float(r[1] or 0) for r in rows}
    except duckdb.CatalogException:
        app.state.preference = {}

    # Uncertainty
    try:
        rows = conn.execute(
            f"""
            SELECT image_sk, uncertainty_score
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
            """
        ).fetchall()
        app.state.uncertainty = {int(r[0]): float(r[1] or 0) for r in rows}
    except duckdb.CatalogException:
        app.state.uncertainty = {}

    # Clusters
    try:
        rows = conn.execute(
            f"""
            SELECT image_sk, cluster_id
            FROM feature_image_cluster
            WHERE cluster_type = 'visual'
              AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
            """
        ).fetchall()
        app.state.clusters = {int(r[0]): int(r[1]) for r in rows}
    except duckdb.CatalogException:
        app.state.clusters = {}

    # Cover fit scores
    try:
        rows = conn.execute(
            f"""
            SELECT image_sk, cover_fit_score
            FROM mart_image_preference_score
            WHERE score_run_id = {LATEST_SCORE_RUN}
            AND cover_fit_score IS NOT NULL
            """
        ).fetchall()
        app.state.cover_fit = {int(r[0]): float(r[1]) for r in rows}
    except (duckdb.CatalogException, duckdb.BinderException):
        app.state.cover_fit = {}

    # Month fit — load from optimization data if available
    app.state.month_fit = {}

    # Embeddings — CLIP 512-dim vectors (requires numpy)
    try:
        import numpy as np

        rows = conn.execute(
            """
            SELECT image_sk, embedding_vector
            FROM feature_image_embedding
            WHERE embedding_type = 'clip'
              AND embedding_run_id = (
                  SELECT embedding_run_id FROM feature_image_embedding
                  WHERE embedding_type = 'clip'
                  ORDER BY created_at DESC LIMIT 1
              )
            """
        ).fetchall()
        app.state.embeddings = {int(r[0]): np.frombuffer(r[1], dtype=np.float32) for r in rows}
    except Exception:
        app.state.embeddings = {}

    logger.info(
        "Cache loaded: %d preference, %d clusters, %d embeddings",
        len(app.state.preference),
        len(app.state.clusters),
        len(app.state.embeddings),
    )
