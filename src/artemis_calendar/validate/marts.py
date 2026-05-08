"""Write validation results to mart tables."""

from __future__ import annotations

import duckdb

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.validate.marts")


def write_bias_detection(
    conn: duckdb.DuckDBPyConnection,
    report: dict,
) -> None:
    """Write bias detection results to mart_bias_detection."""
    conn.execute("DELETE FROM mart_bias_detection WHERE detection_run_id = ?", [report["detection_run_id"]])
    conn.execute(
        """
        INSERT INTO mart_bias_detection (
            detection_run_id, score_run_id,
            position_bias_coeff, position_bias_pvalue, position_bias_detected,
            pairwise_left_win_rate, pairwise_left_pvalue,
            cluster_bias_chi2, cluster_bias_pvalue,
            voter_segment_count, voter_consensus_std,
            score_vs_truth_spearman, score_vs_truth_pvalue,
            alpha_all_voters, alpha_excluding_biased, alpha_delta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            report["detection_run_id"],
            report.get("score_run_id"),
            report.get("position_bias_coeff"),
            report.get("position_bias_pvalue"),
            report.get("position_bias_detected"),
            report.get("pairwise_left_win_rate"),
            report.get("pairwise_left_pvalue"),
            report.get("cluster_bias_chi2"),
            report.get("cluster_bias_pvalue"),
            report.get("voter_segment_count"),
            report.get("voter_consensus_std"),
            report.get("score_vs_truth_spearman"),
            report.get("score_vs_truth_pvalue"),
            report.get("alpha_all_voters"),
            report.get("alpha_excluding_biased"),
            report.get("alpha_delta"),
        ],
    )
    logger.info(f"Wrote bias detection results: {report['detection_run_id']}")


def write_calendar_validation(
    conn: duckdb.DuckDBPyConnection,
    validation_run_id: str,
    method_results: list[dict],
) -> int:
    """Write calendar validation results to mart_calendar_validation.

    Returns count of rows written.
    """
    conn.execute("DELETE FROM mart_calendar_validation WHERE validation_run_id = ?", [validation_run_id])

    if not method_results:
        return 0

    for r in method_results:
        conn.execute(
            """
            INSERT INTO mart_calendar_validation (
                validation_run_id, candidate_name,
                gt_cover_recovered, gt_month_recovered, gt_month_total, gt_recovery_rate,
                slate_cluster_count, slate_max_cosine_sim,
                objective_score, popularity_score, diversity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                validation_run_id,
                r["candidate_name"],
                r.get("gt_cover_recovered"),
                r.get("gt_month_recovered"),
                r.get("gt_month_total"),
                r.get("gt_recovery_rate"),
                r.get("slate_cluster_count"),
                r.get("slate_max_cosine_sim"),
                r.get("objective_score"),
                r.get("popularity_score"),
                r.get("diversity_score"),
            ],
        )

    logger.info(f"Wrote {len(method_results)} calendar validation results: {validation_run_id}")
    return len(method_results)
