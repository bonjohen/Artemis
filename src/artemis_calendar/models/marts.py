"""Write scoring results to mart tables and backfill cluster marts."""

from __future__ import annotations

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.marts")


def write_preference_scores(
    conn: duckdb.DuckDBPyConnection,
    score_run_id: str,
    scores: dict[int, dict],
) -> int:
    """Insert composite scores into mart_image_preference_score.

    Returns count of rows inserted.
    """
    # Clear previous run
    conn.execute("DELETE FROM mart_image_preference_score WHERE score_run_id = ?", [score_run_id])

    rows = []
    for image_sk, s in scores.items():
        rows.append(
            [
                score_run_id,
                image_sk,
                s["shown_count"],
                s["selected_count"],
                s["selection_rate"],
                s.get("wilson_lower"),
                s["elo_score"],
                s["pairwise_wins"],
                s["pairwise_losses"],
                s["btl_score"],
                s["borda_score"],
                s["posterior_mean"],
                s["posterior_lower"],
                s["posterior_upper"],
                s["uncertainty_score"],
                s["polarization_score"],
                s["broad_appeal_score"],
            ]
        )

    if rows:
        import pyarrow as pa

        columns = [
            "score_run_id",
            "image_sk",
            "shown_count",
            "selected_count",
            "selection_rate",
            "wilson_lower",
            "elo_score",
            "pairwise_wins",
            "pairwise_losses",
            "btl_score",
            "borda_score",
            "posterior_mean",
            "posterior_lower",
            "posterior_upper",
            "uncertainty_score",
            "polarization_score",
            "broad_appeal_score",
        ]
        col_data = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        tbl = pa.table(col_data)  # noqa: F841 — referenced by DuckDB SQL below
        col_list = ", ".join(columns)
        conn.execute(f"INSERT INTO mart_image_preference_score ({col_list}) SELECT * FROM tbl")

    logger.info(f"Wrote {len(rows)} preference scores for run {score_run_id}")
    return len(rows)


def write_reliability(
    conn: duckdb.DuckDBPyConnection,
    irr_run_id: str,
    results: dict[str, dict],
) -> int:
    """Insert reliability results into mart_inter_rater_reliability.

    Returns count of rows inserted.
    """
    conn.execute("DELETE FROM mart_inter_rater_reliability WHERE irr_run_id = ?", [irr_run_id])

    rows = []
    for vote_mode, r in results.items():
        rows.append(
            [
                irr_run_id,
                vote_mode,
                None,  # category_sk (NULL for aggregate)
                r["image_count"],
                r["voter_count"],
                r["rating_density"],
                r["krippendorff_alpha"],
                r["fleiss_kappa"],
                r["kendall_w"],
                r["spearman_mean"],
                r["method_notes"],
            ]
        )

    if rows:
        conn.executemany(
            """
            INSERT INTO mart_inter_rater_reliability (
                irr_run_id, vote_mode, category_sk,
                image_count, voter_count, rating_density,
                krippendorff_alpha, fleiss_kappa, kendall_w,
                spearman_mean, method_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    logger.info(f"Wrote {len(rows)} reliability results for run {irr_run_id}")
    return len(rows)


def backfill_cluster_marts(
    conn: duckdb.DuckDBPyConnection,
    score_run_id: str,
) -> int:
    """Backfill preference scores into mart_cluster_top_images and mart_image_cluster_summary.

    Uses the most recent scoring run to populate the NULL score columns
    that were left by Phase 2B's cluster mart builders.

    Returns count of rows updated.
    """
    # Backfill mart_cluster_top_images
    conn.execute(
        """
        UPDATE mart_cluster_top_images t
        SET
            preference_score = s.posterior_mean,
            selection_rate = s.selection_rate,
            elo_score = s.elo_score,
            borda_score = s.borda_score
        FROM mart_image_preference_score s
        WHERE s.score_run_id = ?
          AND s.image_sk = t.image_sk
        """,
        [score_run_id],
    ).fetchone()

    top_count = conn.execute(
        "SELECT count(*) FROM mart_cluster_top_images WHERE preference_score IS NOT NULL"
    ).fetchone()[0]

    # Backfill mart_image_cluster_summary
    conn.execute(
        """
        UPDATE mart_image_cluster_summary cs
        SET
            mean_preference_score = sub.mean_pref,
            max_preference_score = sub.max_pref
        FROM (
            SELECT
                fic.cluster_run_id,
                fic.cluster_type,
                fic.cluster_id,
                AVG(s.posterior_mean) AS mean_pref,
                MAX(s.posterior_mean) AS max_pref
            FROM feature_image_cluster fic
            JOIN mart_image_preference_score s
              ON s.image_sk = fic.image_sk
             AND s.score_run_id = ?
            WHERE fic.cluster_id >= 0
            GROUP BY fic.cluster_run_id, fic.cluster_type, fic.cluster_id
        ) sub
        WHERE cs.cluster_run_id = sub.cluster_run_id
          AND cs.cluster_type = sub.cluster_type
          AND cs.cluster_id = sub.cluster_id
        """,
        [score_run_id],
    )

    summary_count = conn.execute(
        "SELECT count(*) FROM mart_image_cluster_summary WHERE mean_preference_score IS NOT NULL"
    ).fetchone()[0]

    logger.info(
        f"Backfilled cluster marts: {top_count} top-image rows, {summary_count} summary rows with preference scores"
    )
    return top_count + summary_count
