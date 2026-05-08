"""Calendar optimization: select 13 images, assign to months, pick cover."""

from __future__ import annotations

import duckdb
import numpy as np

from artemis_calendar.config.sql_helpers import LATEST_SCORE_RUN, LATEST_VISUAL_CLUSTER_RUN
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status
from artemis_calendar.optimize.assignment import assign_months
from artemis_calendar.optimize.cover_fit import compute_cover_fit_scores
from artemis_calendar.optimize.marts import write_calendar_candidates, write_calendar_month_images
from artemis_calendar.optimize.methods import (
    method_a_top_popularity,
    method_b_cluster_limited,
    method_c_per_cluster,
    method_d_month_first,
    method_e_mmr_greedy,
)
from artemis_calendar.optimize.month_fit import compute_month_fit_scores, load_visual_data
from artemis_calendar.optimize.scoring import score_calendar

logger = get_logger("artemis.optimize")

ALL_METHODS = ("method_a", "method_b", "method_c", "method_d", "method_e")


def run_calendar_optimization(
    conn: duckdb.DuckDBPyConnection,
    methods: tuple[str, ...] = ALL_METHODS,
    seed: int = 42,
) -> dict[str, int | str]:
    """Run full calendar optimization pipeline.

    Steps:
        1. Load preference scores, visual features, embeddings, clusters
        2. Compute month-fit and cover-fit scores
        3. Run each selection method to produce 13-image slates
        4. Assign months via Hungarian algorithm
        5. Score each candidate calendar
        6. Write results to mart tables

    Returns dict with candidate count, run_id, and summary.
    """
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="optimize-calendar",
        dataset_name="mart_calendar_candidate",
        source_name="preference_scores",
    )

    rng = np.random.default_rng(seed)  # noqa: F841 — reserved for future stochastic methods

    # --- Step 1: Load data ---
    logger.info("Loading optimization inputs...")

    # Preference scores (latest run)
    pref_rows = conn.execute(f"""
        SELECT image_sk, posterior_mean, broad_appeal_score, uncertainty_score
        FROM mart_image_preference_score
        WHERE score_run_id = {LATEST_SCORE_RUN}
    """).fetchall()

    preference: dict[int, float] = {}
    broad_appeal: dict[int, float] = {}
    uncertainty: dict[int, float] = {}
    for r in pref_rows:
        sk = int(r[0])
        preference[sk] = float(r[1]) if r[1] is not None else 0.0
        broad_appeal[sk] = float(r[2]) if r[2] is not None else 0.0
        uncertainty[sk] = float(r[3]) if r[3] is not None else 0.0

    image_sks = list(preference.keys())
    logger.info(f"Loaded {len(image_sks)} preference scores")

    # Visual features
    vis_sks, brightness, contrast, saturation, dominant_colors, content_flags = load_visual_data(conn)

    # Clusters (visual, latest run)
    cluster_rows = conn.execute(f"""
        SELECT image_sk, cluster_id
        FROM feature_image_cluster
        WHERE cluster_type = 'visual'
          AND cluster_run_id = {LATEST_VISUAL_CLUSTER_RUN}
          AND cluster_id >= 0
    """).fetchall()
    clusters: dict[int, int] = {int(r[0]): int(r[1]) for r in cluster_rows}

    # CLIP embeddings
    emb_rows = conn.execute("""
        SELECT image_sk, embedding_vector
        FROM feature_image_embedding
    """).fetchall()
    embeddings: dict[int, np.ndarray] = {}
    for r in emb_rows:
        sk = int(r[0])
        vec = r[1]
        if vec is not None:
            embeddings[sk] = np.array(vec, dtype=np.float32)

    logger.info(f"Loaded {len(clusters)} cluster assignments, {len(embeddings)} embeddings")

    # --- Step 2: Month-fit and cover-fit ---
    month_fit = compute_month_fit_scores(image_sks, brightness, contrast, saturation, dominant_colors, content_flags)
    cover_fit = compute_cover_fit_scores(image_sks, broad_appeal, contrast, saturation)

    # --- Step 3-5: Run methods, assign months, score ---
    method_funcs = {
        "method_a": lambda: method_a_top_popularity(image_sks, preference),
        "method_b": lambda: method_b_cluster_limited(image_sks, preference, clusters),
        "method_c": lambda: method_c_per_cluster(image_sks, preference, clusters),
        "method_d": lambda: method_d_month_first(image_sks, preference, month_fit, clusters),
        "method_e": lambda: method_e_mmr_greedy(
            image_sks,
            preference,
            broad_appeal,
            month_fit,
            uncertainty,
            embeddings,
            clusters,
        ),
    }

    # Clear previous run's month-image assignments
    conn.execute("DELETE FROM mart_calendar_candidate_month_image WHERE candidate_run_id = ?", [run_id])

    candidates = []
    total_month_rows = 0

    for method_name in methods:
        func = method_funcs.get(method_name)
        if func is None:
            logger.warning(f"Unknown method: {method_name}, skipping")
            continue

        # Select 13 images
        selected = func()
        if len(selected) < 13:
            logger.warning(f"{method_name}: only selected {len(selected)} images (need 13)")

        # Assign months
        assignments = assign_months(selected, month_fit)

        # Score the calendar
        scores = score_calendar(
            selected,
            assignments,
            preference,
            month_fit,
            cover_fit,
            uncertainty,
            clusters,
            embeddings,
        )
        scores["candidate_name"] = method_name

        candidates.append(scores)

        # Write month-image assignments
        # Compute per-image month-fit for the assigned month
        assigned_month_fits = {}
        for sk, seq, _label in assignments:
            mf = month_fit.get(sk)
            if mf is not None and 0 < seq <= 13:
                assigned_month_fits[sk] = float(mf[seq - 1])

        rows = write_calendar_month_images(
            conn,
            run_id,
            method_name,
            assignments,
            assigned_month_fits,
            preference,
        )
        total_month_rows += rows

        logger.info(
            f"{method_name}: objective={scores['objective_score']:.3f}, "
            f"popularity={scores['popularity_score']:.3f}, "
            f"diversity={scores['diversity_score']:.3f}, "
            f"cover={scores['cover_image_sk']}"
        )

    # --- Step 6: Write candidate summaries ---
    candidate_count = write_calendar_candidates(conn, run_id, candidates)

    update_run_status(
        conn,
        run_id,
        row_count_raw=candidate_count,
        row_count_loaded=candidate_count,
        load_status="complete",
    )

    result = {
        "candidates": candidate_count,
        "month_image_rows": total_month_rows,
        "candidate_run_id": run_id,
    }
    logger.info(f"Optimization complete: {result}")
    return result
