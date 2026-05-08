"""S4: Calendar optimization validation — evaluate optimizer against ground truth."""

from __future__ import annotations

import duckdb
import numpy as np

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.validate.calendar")


def compute_ground_truth_recovery(conn: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """For each candidate calendar, compute how many ground-truth images it recovers.

    Ground truth roles: 'cover' and 'month' from synthetic_image_truth.
    Returns dict keyed by candidate_name.
    """
    # Get ground-truth image sets
    gt_rows = conn.execute(
        """
        SELECT image_sk, ground_truth_calendar_role
        FROM synthetic_image_truth
        WHERE ground_truth_calendar_role IN ('cover', 'month')
        """
    ).fetchall()

    if not gt_rows:
        logger.warning("No ground-truth calendar images found")
        return {}

    gt_cover_sks = {r[0] for r in gt_rows if r[1] == "cover"}
    gt_month_sks = {r[0] for r in gt_rows if r[1] == "month"}
    gt_all_sks = gt_cover_sks | gt_month_sks
    gt_total = len(gt_all_sks)

    # Get all candidates and their slates
    candidates = conn.execute(
        """
        SELECT candidate_name, cover_image_sk
        FROM mart_calendar_candidate
        ORDER BY candidate_name
        """
    ).fetchall()

    if not candidates:
        logger.warning("No calendar candidates found")
        return {}

    results = {}
    for candidate_name, cover_image_sk in candidates:
        slate_rows = conn.execute(
            """
            SELECT image_sk
            FROM mart_calendar_candidate_month_image
            WHERE candidate_name = ?
            """,
            [candidate_name],
        ).fetchall()

        slate_sks = {r[0] for r in slate_rows}
        recovered = slate_sks & gt_all_sks
        cover_recovered = cover_image_sk in gt_cover_sks if gt_cover_sks else None

        results[candidate_name] = {
            "gt_cover_recovered": cover_recovered,
            "gt_month_recovered": len(recovered),
            "gt_month_total": gt_total,
            "gt_recovery_rate": len(recovered) / gt_total if gt_total > 0 else 0.0,
        }

    logger.info(
        "Ground-truth recovery: "
        + ", ".join(f"{k}={v['gt_month_recovered']}/{v['gt_month_total']}" for k, v in results.items())
    )
    return results


def compute_slate_diversity(conn: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """For each candidate, compute visual cluster diversity and max CLIP similarity.

    Returns dict keyed by candidate_name.
    """
    candidates = conn.execute(
        "SELECT DISTINCT candidate_name FROM mart_calendar_candidate ORDER BY candidate_name"
    ).fetchall()

    if not candidates:
        return {}

    results = {}
    for (candidate_name,) in candidates:
        slate_rows = conn.execute(
            """
            SELECT image_sk
            FROM mart_calendar_candidate_month_image
            WHERE candidate_name = ?
            """,
            [candidate_name],
        ).fetchall()

        slate_sks = [r[0] for r in slate_rows]
        if not slate_sks:
            results[candidate_name] = {"slate_cluster_count": 0, "slate_max_cosine_sim": None}
            continue

        # Count distinct visual clusters
        placeholders = ", ".join(["?"] * len(slate_sks))
        cluster_count = conn.execute(
            f"""
            SELECT count(DISTINCT cluster_label)
            FROM feature_image_cluster
            WHERE cluster_type = 'visual' AND image_sk IN ({placeholders})
            """,
            slate_sks,
        ).fetchone()[0]

        # Compute max pairwise CLIP cosine similarity
        max_cosine = _compute_max_cosine_similarity(conn, slate_sks)

        results[candidate_name] = {
            "slate_cluster_count": int(cluster_count) if cluster_count else 0,
            "slate_max_cosine_sim": max_cosine,
        }

    logger.info(
        "Slate diversity: "
        + ", ".join(
            f"{k}: clusters={v['slate_cluster_count']}, max_sim={v['slate_max_cosine_sim']}" for k, v in results.items()
        )
    )
    return results


def _compute_max_cosine_similarity(conn: duckdb.DuckDBPyConnection, image_sks: list[int]) -> float | None:
    """Compute maximum pairwise cosine similarity among a set of images using CLIP embeddings."""
    if len(image_sks) < 2:
        return None

    placeholders = ", ".join(["?"] * len(image_sks))
    rows = conn.execute(
        f"""
        SELECT image_sk, embedding_vector
        FROM feature_image_embedding
        WHERE image_sk IN ({placeholders})
        """,
        image_sks,
    ).fetchall()

    if len(rows) < 2:
        return None

    # Build embedding matrix
    vectors = []
    for _, embedding in rows:
        vectors.append(np.array(embedding, dtype=np.float32))

    # Pairwise cosine similarity
    max_sim = -1.0
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            dot = np.dot(vectors[i], vectors[j])
            norm_i = np.linalg.norm(vectors[i])
            norm_j = np.linalg.norm(vectors[j])
            if norm_i > 0 and norm_j > 0:
                sim = float(dot / (norm_i * norm_j))
                max_sim = max(max_sim, sim)

    return max_sim if max_sim > -1.0 else None


def run_calendar_validation(conn: duckdb.DuckDBPyConnection) -> dict:
    """Orchestrator: run all calendar validation analyses and persist results.

    Returns comparison report dict.
    """
    from artemis_calendar.observe.run_manifest import generate_run_id
    from artemis_calendar.validate.marts import write_calendar_validation

    logger.info("Starting calendar optimization validation (S4)...")

    recovery = compute_ground_truth_recovery(conn)
    diversity = compute_slate_diversity(conn)

    if not recovery:
        logger.warning("No recovery data — skipping validation write")
        return {"methods": {}}

    # Merge with existing candidate scores
    candidate_scores = conn.execute(
        """
        SELECT candidate_name, objective_score, popularity_score, diversity_score
        FROM mart_calendar_candidate
        ORDER BY candidate_name
        """
    ).fetchall()
    score_map = {
        r[0]: {"objective_score": r[1], "popularity_score": r[2], "diversity_score": r[3]} for r in candidate_scores
    }

    validation_run_id = generate_run_id()
    method_results = []
    for candidate_name, rec in recovery.items():
        div = diversity.get(candidate_name, {})
        scores = score_map.get(candidate_name, {})
        method_results.append(
            {
                "candidate_name": candidate_name,
                **rec,
                **div,
                **scores,
            }
        )

    write_calendar_validation(conn, validation_run_id, method_results)

    # Build report
    report = {
        "validation_run_id": validation_run_id,
        "methods": {r["candidate_name"]: r for r in method_results},
    }

    # Log summary comparison
    logger.info("Calendar validation complete:")
    for r in method_results:
        logger.info(
            f"  {r['candidate_name']}: recovery={r.get('gt_recovery_rate', 0):.2%}, "
            f"clusters={r.get('slate_cluster_count', 'N/A')}, "
            f"max_sim={r.get('slate_max_cosine_sim', 'N/A')}, "
            f"objective={r.get('objective_score', 'N/A')}"
        )

    return report
