"""Image deduplication via CLIP embedding cosine similarity.

Finds near-duplicate images, groups them, picks a master per group,
and suppresses the rest via dim_image.is_suppressed.
"""

from __future__ import annotations

import time

import duckdb
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from artemis_calendar.config.settings import DB_PATH
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import generate_run_id

logger = get_logger("artemis.features.dedup")


def find_duplicates(
    conn: duckdb.DuckDBPyConnection | None = None,
    threshold: float = 0.98,
    batch_size: int = 1000,
    progress_callback=None,
) -> dict:
    """Find and group near-duplicate images by CLIP cosine similarity.

    Args:
        conn: DuckDB connection. Opens warehouse if None.
        threshold: Cosine similarity threshold for duplicate detection.
        batch_size: Rows per similarity computation batch.
        progress_callback: Called with (done, total, elapsed).

    Returns summary dict.
    """
    own_conn = conn is None
    if own_conn:
        conn = duckdb.connect(str(DB_PATH))

    run_id = generate_run_id()
    logger.info(f"Starting dedup run {run_id} with threshold={threshold}")

    # Load all CLIP embeddings
    t0 = time.time()
    rows = conn.execute(
        """
        SELECT e.image_sk, e.embedding_vector
        FROM feature_image_embedding e
        JOIN dim_image d ON e.image_sk = d.image_sk
        WHERE d.vote_pool_flag = true
        ORDER BY e.image_sk
        """
    ).fetchall()

    n = len(rows)
    logger.info(f"Loaded {n} embeddings in {time.time() - t0:.1f}s")

    image_sks = np.array([int(r[0]) for r in rows])
    embeddings = np.array([list(r[1]) for r in rows], dtype=np.float32)

    # L2-normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms

    # Find pairs above threshold using batched matrix multiply
    logger.info(f"Computing pairwise similarities (batch_size={batch_size})...")
    t1 = time.time()

    pair_rows = []
    pair_cols = []

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        # Cosine similarity of batch against all embeddings
        sim = embeddings[start:end] @ embeddings.T  # (batch, n)

        for i_local in range(end - start):
            i_global = start + i_local
            # Only check upper triangle (j > i)
            sims = sim[i_local, i_global + 1:]
            above = np.where(sims >= threshold)[0]
            for j_offset in above:
                j_global = i_global + 1 + j_offset
                pair_rows.append(i_global)
                pair_cols.append(j_global)

        elapsed = time.time() - t1
        if progress_callback:
            progress_callback(end, n, elapsed)

    logger.info(
        f"Found {len(pair_rows)} pairs above {threshold} "
        f"in {time.time() - t1:.1f}s"
    )

    if not pair_rows:
        logger.info("No duplicates found.")
        if own_conn:
            conn.close()
        return {
            "run_id": run_id,
            "threshold": threshold,
            "total_images": n,
            "duplicate_pairs": 0,
            "groups": 0,
            "images_suppressed": 0,
        }

    # Build sparse adjacency and find connected components
    data = np.ones(len(pair_rows) * 2, dtype=np.int8)
    row_idx = np.array(pair_rows + pair_cols)
    col_idx = np.array(pair_cols + pair_rows)
    adj = csr_matrix((data, (row_idx, col_idx)), shape=(n, n))

    n_components, labels = connected_components(adj, directed=False)

    # Group components with 2+ members
    from collections import defaultdict

    groups_map = defaultdict(list)
    for idx, label in enumerate(labels):
        groups_map[label].append(idx)

    multi_groups = {k: v for k, v in groups_map.items() if len(v) >= 2}
    logger.info(f"Connected components: {n_components} total, {len(multi_groups)} with 2+ members")

    # Load preference scores for master selection
    score_rows = conn.execute(
        """
        SELECT image_sk, COALESCE(posterior_mean, 0) AS score
        FROM mart_image_preference_score
        """
    ).fetchall()
    score_map = {int(r[0]): float(r[1]) for r in score_rows}

    # Load brightness for tie-breaking
    bright_rows = conn.execute(
        "SELECT image_sk, COALESCE(brightness_score, 0) FROM feature_image_visual"
    ).fetchall()
    bright_map = {int(r[0]): float(r[1]) for r in bright_rows}

    # Build groups and pick masters
    import pyarrow as pa

    group_records = []
    member_records = []
    suppressed_sks = []

    for group_label, member_indices in multi_groups.items():
        member_sks_list = [int(image_sks[i]) for i in member_indices]

        # Pick master: highest preference score, tie-break on brightness
        best_sk = max(
            member_sks_list,
            key=lambda sk: (score_map.get(sk, 0), bright_map.get(sk, 0)),
        )

        group_id = f"dedup_{run_id}_{group_label}"

        group_records.append((
            group_id, best_sk, len(member_sks_list), threshold, run_id,
        ))

        # Compute similarity to master for each member
        master_idx = member_indices[member_sks_list.index(best_sk)]
        master_emb = embeddings[master_idx]

        for idx, sk in zip(member_indices, member_sks_list):
            sim_to_master = float(embeddings[idx] @ master_emb)
            is_master = sk == best_sk
            member_records.append((group_id, sk, round(sim_to_master, 6), is_master))
            if not is_master:
                suppressed_sks.append(sk)

    # Write groups
    if group_records:
        tbl = pa.table({
            "group_id": [r[0] for r in group_records],
            "master_image_sk": pa.array([r[1] for r in group_records], type=pa.int64()),
            "member_count": [r[2] for r in group_records],
            "similarity_threshold": [r[3] for r in group_records],
            "dedup_run_id": [r[4] for r in group_records],
        })
        conn.register("_grp", tbl)
        conn.execute("""
            INSERT INTO dedup_image_group
                (group_id, master_image_sk, member_count, similarity_threshold, dedup_run_id)
            SELECT * FROM _grp
        """)
        conn.unregister("_grp")

    # Write members
    if member_records:
        tbl = pa.table({
            "group_id": [r[0] for r in member_records],
            "image_sk": pa.array([r[1] for r in member_records], type=pa.int64()),
            "similarity_to_master": [r[2] for r in member_records],
            "is_master": [r[3] for r in member_records],
        })
        conn.register("_mem", tbl)
        conn.execute("""
            INSERT INTO dedup_image_member
                (group_id, image_sk, similarity_to_master, is_master)
            SELECT * FROM _mem
        """)
        conn.unregister("_mem")

    # Suppress non-master images
    if suppressed_sks:
        # Batch update in chunks
        for i in range(0, len(suppressed_sks), 500):
            chunk = suppressed_sks[i : i + 500]
            placeholders = ", ".join("?" * len(chunk))
            conn.execute(
                f"UPDATE dim_image SET is_suppressed = true WHERE image_sk IN ({placeholders})",
                chunk,
            )

    summary = {
        "run_id": run_id,
        "threshold": threshold,
        "total_images": n,
        "duplicate_pairs": len(pair_rows),
        "groups": len(multi_groups),
        "images_suppressed": len(suppressed_sks),
        "images_retained": n - len(suppressed_sks),
    }

    logger.info(
        f"Dedup complete: {summary['groups']} groups, "
        f"{summary['images_suppressed']} suppressed, "
        f"{summary['images_retained']} retained"
    )

    if own_conn:
        conn.close()

    return summary


def restore_all(
    conn: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> int:
    """Restore all suppressed images from a dedup run (or all runs if run_id is None).

    Returns number of images restored.
    """
    own_conn = conn is None
    if own_conn:
        conn = duckdb.connect(str(DB_PATH))

    if run_id:
        # Restore only images from this run
        count = conn.execute(
            """
            UPDATE dim_image SET is_suppressed = false
            WHERE image_sk IN (
                SELECT m.image_sk FROM dedup_image_member m
                JOIN dedup_image_group g ON m.group_id = g.group_id
                WHERE g.dedup_run_id = ? AND m.is_master = false
            )
            """,
            [run_id],
        ).fetchone()[0]
        conn.execute(
            "DELETE FROM dedup_image_member WHERE group_id IN "
            "(SELECT group_id FROM dedup_image_group WHERE dedup_run_id = ?)",
            [run_id],
        )
        conn.execute(
            "DELETE FROM dedup_image_group WHERE dedup_run_id = ?", [run_id]
        )
    else:
        count = conn.execute(
            "UPDATE dim_image SET is_suppressed = false WHERE is_suppressed = true"
        ).fetchone()[0]
        conn.execute("DELETE FROM dedup_image_member")
        conn.execute("DELETE FROM dedup_image_group")

    logger.info(f"Restored {count} images (run_id={run_id or 'all'})")

    if own_conn:
        conn.close()

    return count


def get_dedup_summary(conn: duckdb.DuckDBPyConnection) -> dict:
    """Get summary statistics for dedup results."""
    groups = conn.execute("SELECT count(*) FROM dedup_image_group").fetchone()[0]
    suppressed = conn.execute(
        "SELECT count(*) FROM dim_image WHERE is_suppressed = true"
    ).fetchone()[0]
    active = conn.execute(
        "SELECT count(*) FROM dim_image WHERE vote_pool_flag = true AND COALESCE(is_suppressed, false) = false"
    ).fetchone()[0]

    # Size distribution
    sizes = conn.execute(
        "SELECT member_count, count(*) FROM dedup_image_group GROUP BY member_count ORDER BY member_count"
    ).fetchall()

    return {
        "groups": groups,
        "suppressed": suppressed,
        "active_images": active,
        "size_distribution": [{"size": int(r[0]), "count": int(r[1])} for r in sizes],
    }
