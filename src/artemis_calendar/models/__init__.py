"""Statistical modeling: preference scoring and inter-rater reliability."""

from __future__ import annotations

import duckdb

from artemis_calendar.models.batch_scores import compute_batch_scores, compute_polarization
from artemis_calendar.models.category_scores import compute_borda_scores
from artemis_calendar.models.composite import compute_composite_scores
from artemis_calendar.models.marts import backfill_cluster_marts, write_preference_scores, write_reliability
from artemis_calendar.models.pairwise_scores import compute_elo_scores
from artemis_calendar.models.reliability import compute_reliability
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.models")


def compute_preference_scores(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Run full preference scoring pipeline.

    Steps:
        1. Compute batch selection scores (selection rate, Wilson, Beta posterior)
        2. Compute Elo scores from pairwise votes
        3. Compute Borda scores from category rankings
        4. Compute polarization from voter disagreement
        5. Merge into composite scores with uncertainty and appeal metrics
        6. Write to mart_image_preference_score
        7. Compute inter-rater reliability
        8. Write to mart_inter_rater_reliability
        9. Backfill cluster mart tables

    Returns dict with row counts for each output.
    """
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="compute-scores",
        dataset_name="mart_image_preference_score",
        source_name="vote_facts",
    )

    # Get all vote-pool image SKs
    all_image_sks = [
        int(r[0]) for r in conn.execute("SELECT image_sk FROM dim_image WHERE vote_pool_flag = true").fetchall()
    ]

    logger.info(f"Computing preference scores for {len(all_image_sks)} vote-pool images")

    # Step 1-4: Compute individual score components
    batch_scores = compute_batch_scores(conn)
    elo_scores = compute_elo_scores(conn)
    borda_scores = compute_borda_scores(conn)
    polarization = compute_polarization(conn)

    # Step 5: Composite
    composite = compute_composite_scores(
        batch_scores=batch_scores,
        elo_scores=elo_scores,
        borda_scores=borda_scores,
        polarization=polarization,
        all_image_sks=all_image_sks,
    )

    # Step 6: Write preference scores
    pref_count = write_preference_scores(conn, run_id, composite)

    # Step 7-8: Reliability
    reliability = compute_reliability(conn)
    irr_count = write_reliability(conn, run_id, reliability)

    # Step 9: Backfill cluster marts
    backfill_count = backfill_cluster_marts(conn, run_id)

    update_run_status(
        conn,
        run_id,
        row_count_raw=pref_count,
        row_count_loaded=pref_count,
        load_status="complete",
    )

    counts = {
        "preference_scores": pref_count,
        "reliability_results": irr_count,
        "cluster_backfill": backfill_count,
        "score_run_id": run_id,
    }

    logger.info(f"Scoring complete: {counts}")
    return counts
