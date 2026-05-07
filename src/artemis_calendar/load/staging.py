"""Load parsed records into staging tables."""

import duckdb


def load_timeline_photos(conn: duckdb.DuckDBPyConnection, run_id: str, photos: list[dict]) -> int:
    """Insert parsed timeline photos into stg_timeline_photo. Returns row count."""
    rows = []
    for p in photos:
        rows.append(
            (
                run_id,
                p.get("file"),
                p.get("title"),
                p.get("flickr_desc"),
                p.get("photographer"),
                p.get("location"),
                p.get("camera"),
                p.get("settings"),
                p.get("time"),
                p.get("spacecraft"),
                p.get("batch"),
                p.get("enabled"),
                p.get("camera_id"),
            )
        )
    conn.executemany(
        """INSERT INTO stg_timeline_photo
           (load_run_id, file_name, title, description, photographer, location,
            camera, settings, time_str, spacecraft, batch, enabled, camera_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def load_vote_manifest_images(conn: duckdb.DuckDBPyConnection, run_id: str, items: list[dict]) -> int:
    """Insert parsed vote manifest items into stg_vote_manifest_image. Returns row count."""
    if not items:
        return 0
    guids = [item["guid"] for item in items]
    links = [item.get("link") for item in items]
    conn.execute(
        """
        INSERT INTO stg_vote_manifest_image (load_run_id, guid, nasa_link)
        SELECT ?, unnest(?::TEXT[]), unnest(?::TEXT[])
        """,
        [run_id, guids, links],
    )
    return len(items)


def load_categories(conn: duckdb.DuckDBPyConnection, run_id: str, categories: list[dict]) -> int:
    """Insert parsed categories into stg_category. Returns row count."""
    rows = [(run_id, c["key"], c.get("slug"), c.get("label"), c.get("count"), c.get("showcase")) for c in categories]
    conn.executemany(
        """INSERT INTO stg_category
           (load_run_id, category_key, category_slug, category_label, image_count, showcase_guid)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def load_batch_leaderboard(conn: duckdb.DuckDBPyConnection, run_id: str, entries: list[dict]) -> int:
    """Insert parsed batch leaderboard into stg_leaderboard_batch. Returns row count."""
    rows = [(run_id, e["guid"], e.get("picks"), e.get("shown"), e.get("rate"), e.get("wilson")) for e in entries]
    conn.executemany(
        """INSERT INTO stg_leaderboard_batch
           (load_run_id, guid, picks, shown, rate, wilson)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def load_elo_leaderboard(conn: duckdb.DuckDBPyConnection, run_id: str, entries: list[dict]) -> int:
    """Insert parsed Elo leaderboard into stg_leaderboard_elo. Returns row count."""
    rows = [(run_id, e["guid"], e.get("elo"), e.get("wins"), e.get("losses")) for e in entries]
    conn.executemany(
        """INSERT INTO stg_leaderboard_elo (load_run_id, guid, elo, wins, losses) VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def load_vote_counts(conn: duckdb.DuckDBPyConnection, run_id: str, data: dict) -> int:
    """Insert parsed vote counts into stg_vote_counts. Returns 1."""
    conn.execute(
        "INSERT INTO stg_vote_counts (load_run_id, ballot_count, unique_picked) VALUES (?, ?, ?)",
        [run_id, data.get("count"), data.get("unique_picked")],
    )
    return 1
