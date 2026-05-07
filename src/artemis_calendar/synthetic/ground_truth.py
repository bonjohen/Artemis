"""Assign synthetic latent appeal scores to images for testing."""

import hashlib

import duckdb


def assign_ground_truth(conn: duckdb.DuckDBPyConnection, synthetic_run_id: str, seed: int) -> int:
    """Assign latent appeal scores to all vote-pool images.

    Heuristics:
    - Base appeal from a hash of the GUID + seed (deterministic pseudo-random)
    - Timeline images get a boost (they were curated)
    - Enabled images get a boost
    - Category showcase images get the highest boost
    """
    images = conn.execute(
        "SELECT image_sk, source_image_id, timeline_flag, enabled_flag FROM dim_image WHERE vote_pool_flag = true"
    ).fetchall()

    if not images:
        return 0

    # Get showcase GUIDs
    showcase_guids = set()
    try:
        rows = conn.execute("SELECT showcase_guid FROM stg_category WHERE showcase_guid IS NOT NULL").fetchall()
        showcase_guids = {r[0] for r in rows}
    except Exception:
        pass

    run_ids = []
    image_sks = []
    appeals = []
    dramas = []
    covers = []
    roles = []

    for image_sk, guid, timeline_flag, enabled_flag in images:
        h = hashlib.sha256(f"{guid}:{seed}".encode()).hexdigest()
        base_appeal = int(h[:8], 16) / 0xFFFFFFFF

        h2 = hashlib.sha256(f"drama:{guid}:{seed}".encode()).hexdigest()
        visual_drama = int(h2[:8], 16) / 0xFFFFFFFF

        h3 = hashlib.sha256(f"cover:{guid}:{seed}".encode()).hexdigest()
        cover_value = int(h3[:8], 16) / 0xFFFFFFFF

        if timeline_flag:
            base_appeal = min(1.0, base_appeal + 0.15)
            visual_drama = min(1.0, visual_drama + 0.10)
        if enabled_flag:
            base_appeal = min(1.0, base_appeal + 0.05)
        if guid in showcase_guids:
            base_appeal = min(1.0, base_appeal + 0.25)
            cover_value = min(1.0, cover_value + 0.20)

        role = "distractor"
        if base_appeal > 0.85:
            role = "month"
        if base_appeal > 0.90 and cover_value > 0.70:
            role = "cover"

        run_ids.append(synthetic_run_id)
        image_sks.append(image_sk)
        appeals.append(base_appeal)
        dramas.append(visual_drama)
        covers.append(cover_value)
        roles.append(role)

    conn.execute("DELETE FROM synthetic_image_truth WHERE synthetic_run_id = ?", [synthetic_run_id])
    conn.execute(
        """INSERT INTO synthetic_image_truth
           (synthetic_run_id, image_sk, latent_general_appeal, latent_visual_drama,
            latent_cover_value, ground_truth_calendar_role)
        SELECT unnest(?::TEXT[]), unnest(?::BIGINT[]), unnest(?::DOUBLE[]),
               unnest(?::DOUBLE[]), unnest(?::DOUBLE[]), unnest(?::TEXT[])""",
        [run_ids, image_sks, appeals, dramas, covers, roles],
    )
    return len(image_sks)
