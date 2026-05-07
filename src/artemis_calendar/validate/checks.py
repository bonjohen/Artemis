"""Data quality checks for the warehouse."""

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.validate")


def check_row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Return row counts for all warehouse tables."""
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_name != '_migrations'"
    ).fetchall()
    counts = {}
    for (table_name,) in tables:
        count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        counts[table_name] = count
    return counts


def check_duplicate_guids(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Check for duplicate source_image_id in dim_image."""
    dupes = conn.execute(
        "SELECT source_image_id FROM dim_image GROUP BY source_image_id HAVING count(*) > 1"
    ).fetchall()
    if dupes:
        dupe_ids = [d[0] for d in dupes]
        logger.warning(f"Duplicate source_image_ids in dim_image: {dupe_ids}")
        return dupe_ids
    return []


def run_all_checks(conn: duckdb.DuckDBPyConnection) -> dict:
    """Run all validation checks and return results."""
    results = {
        "row_counts": check_row_counts(conn),
        "duplicate_guids": check_duplicate_guids(conn),
    }
    logger.info(f"Validation complete: {len(results['duplicate_guids'])} duplicate GUIDs found")
    return results
