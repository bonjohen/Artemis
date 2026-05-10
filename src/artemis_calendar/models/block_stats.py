"""Block-aware statistical analysis: lift, similarity, score impact, calendar impact."""

from __future__ import annotations

import json

import duckdb
import numpy as np
from scipy import stats

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.block_stats")


def compute_attribute_lift(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
) -> list[dict]:
    """Compute attribute lift for each block: block selection rate / global rate.

    Returns list of dicts ready for mart_voting_block_attribute_lift.
    """
    # Global selection rate per attribute (vote-level, not distinct-image)
    global_rates = conn.execute(
        """
        SELECT fa.attribute_code,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END) as selected,
               count(*) as exposed
        FROM fact_batch_ballot_image bbi
        JOIN feature_image_attribute fa ON bbi.image_sk = fa.image_sk
        WHERE bbi.synthetic_flag = true AND fa.is_accepted = true
          AND fa.label_source != 'derived_rule'
        GROUP BY fa.attribute_code
        """
    ).fetchall()
    global_map = {r[0]: (r[1], r[2]) for r in global_rates}

    # Per-block selection rate per attribute (vote-level)
    block_rates = conn.execute(
        """
        SELECT sva.block_id, fa.attribute_code,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END) as selected,
               count(*) as exposed
        FROM fact_batch_ballot_image bbi
        JOIN synthetic_voter_block_assignment sva
            ON bbi.voter_sk = sva.voter_sk AND sva.scenario_id = ?
        JOIN feature_image_attribute fa ON bbi.image_sk = fa.image_sk
        WHERE bbi.synthetic_flag = true AND fa.is_accepted = true
          AND fa.label_source != 'derived_rule'
        GROUP BY sva.block_id, fa.attribute_code
        """,
        [scenario_id],
    ).fetchall()

    results = []
    for block_id, attr_code, block_sel, block_exp in block_rates:
        global_sel, global_exp = global_map.get(attr_code, (0, 0))
        block_rate = block_sel / max(block_exp, 1)
        global_rate = global_sel / max(global_exp, 1)
        lift = block_rate / max(global_rate, 1e-10)

        # Odds ratio
        a = block_sel
        b = max(block_exp - block_sel, 1)
        c = max(global_sel - block_sel, 1)
        d = max(global_exp - global_sel - b, 1)
        odds_ratio = (a * d) / max(b * c, 1)

        # Wilson confidence interval for block rate
        n = max(block_exp, 1)
        p_hat = block_rate
        z = 1.96
        denom = 1 + z * z / n
        center = (p_hat + z * z / (2 * n)) / denom
        spread = z * np.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denom
        ci_low = max(0, center - spread)
        ci_high = min(1, center + spread)

        results.append(
            {
                "scenario_id": scenario_id,
                "block_id": block_id,
                "attribute_code": attr_code,
                "block_selection_rate": round(block_rate, 6),
                "global_selection_rate": round(global_rate, 6),
                "lift": round(lift, 4),
                "odds_ratio": round(odds_ratio, 4),
                "selected_count": int(block_sel),
                "exposed_count": int(block_exp),
                "confidence_interval_low": round(ci_low, 6),
                "confidence_interval_high": round(ci_high, 6),
            }
        )

    return results


def compute_cluster_lift(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
) -> list[dict]:
    """Compute cluster lift per block: block cluster selection vs expected."""
    # Global cluster selection counts (vote-level)
    global_clusters = conn.execute(
        """
        SELECT fic.cluster_id, fic.cluster_label,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END) as selected,
               count(*) as exposed
        FROM fact_batch_ballot_image bbi
        JOIN feature_image_cluster fic ON bbi.image_sk = fic.image_sk
        WHERE bbi.synthetic_flag = true AND fic.cluster_type = 'visual'
        GROUP BY fic.cluster_id, fic.cluster_label
        """
    ).fetchall()
    global_map = {r[0]: (r[1], r[2], r[3]) for r in global_clusters}
    total_global_selected = sum(r[2] for r in global_clusters)

    # Per-block cluster selections (vote-level)
    block_clusters = conn.execute(
        """
        SELECT sva.block_id, fic.cluster_id, fic.cluster_label,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END) as selected,
               count(*) as exposed
        FROM fact_batch_ballot_image bbi
        JOIN synthetic_voter_block_assignment sva
            ON bbi.voter_sk = sva.voter_sk AND sva.scenario_id = ?
        JOIN feature_image_cluster fic ON bbi.image_sk = fic.image_sk
        WHERE bbi.synthetic_flag = true AND fic.cluster_type = 'visual'
        GROUP BY sva.block_id, fic.cluster_id, fic.cluster_label
        """,
        [scenario_id],
    ).fetchall()

    results = []
    for block_id, cluster_id, cluster_label, block_sel, block_exp in block_clusters:
        global_label, global_sel, global_exp = global_map.get(cluster_id, (cluster_label, 0, 0))
        block_rate = block_sel / max(block_exp, 1)
        global_rate = global_sel / max(global_exp, 1)
        lift = block_rate / max(global_rate, 1e-10)

        # Expected count under null (proportional to global)
        block_total_sel = block_sel  # rough approximation
        expected = (global_sel / max(total_global_selected, 1)) * block_total_sel if total_global_selected else 0
        chi_sq = ((block_sel - expected) ** 2) / max(expected, 1e-10)

        results.append(
            {
                "scenario_id": scenario_id,
                "block_id": block_id,
                "cluster_id": int(cluster_id),
                "cluster_label": global_label or cluster_label,
                "block_selection_rate": round(block_rate, 6),
                "global_selection_rate": round(global_rate, 6),
                "lift": round(lift, 4),
                "chi_square_contribution": round(chi_sq, 4),
                "selected_count": int(block_sel),
                "expected_count": round(expected, 2),
            }
        )

    return results


def compute_block_similarity(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
    top_n: int = 50,
) -> list[dict]:
    """Compute pairwise similarity between voting blocks."""
    # Get top-N selected images per block
    block_top = conn.execute(
        """
        SELECT sva.block_id, bbi.image_sk, count(*) as cnt
        FROM fact_batch_ballot_image bbi
        JOIN synthetic_voter_block_assignment sva
            ON bbi.voter_sk = sva.voter_sk AND sva.scenario_id = ?
        WHERE bbi.was_selected = true AND bbi.synthetic_flag = true
        GROUP BY sva.block_id, bbi.image_sk
        ORDER BY sva.block_id, cnt DESC
        """,
        [scenario_id],
    ).fetchall()

    # Build per-block top sets and score vectors
    block_images: dict[str, list[tuple[int, int]]] = {}
    for block_id, image_sk, cnt in block_top:
        if block_id not in block_images:
            block_images[block_id] = []
        block_images[block_id].append((int(image_sk), int(cnt)))

    block_top_sets: dict[str, set[int]] = {}
    block_score_vectors: dict[str, dict[int, int]] = {}
    for block_id, imgs in block_images.items():
        block_top_sets[block_id] = {sk for sk, _ in imgs[:top_n]}
        block_score_vectors[block_id] = {sk: cnt for sk, cnt in imgs}

    block_ids = sorted(block_images.keys())
    results = []

    for i, block_a in enumerate(block_ids):
        for block_b in block_ids[i + 1 :]:
            set_a = block_top_sets.get(block_a, set())
            set_b = block_top_sets.get(block_b, set())

            # Jaccard
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            jaccard = intersection / max(union, 1)

            # Cosine similarity of score vectors
            all_sks = set(block_score_vectors.get(block_a, {}).keys()) | set(
                block_score_vectors.get(block_b, {}).keys()
            )
            if all_sks:
                vec_a = np.array([block_score_vectors.get(block_a, {}).get(sk, 0) for sk in all_sks])
                vec_b = np.array([block_score_vectors.get(block_b, {}).get(sk, 0) for sk in all_sks])
                norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
                cosine = float(np.dot(vec_a, vec_b) / max(norm, 1e-10))
            else:
                cosine = 0.0

            # Spearman correlation on shared images
            shared = set_a & set_b
            if len(shared) >= 3:
                scores_a = [block_score_vectors.get(block_a, {}).get(sk, 0) for sk in shared]
                scores_b = [block_score_vectors.get(block_b, {}).get(sk, 0) for sk in shared]
                corr, _ = stats.spearmanr(scores_a, scores_b)
                score_corr = float(corr) if not np.isnan(corr) else 0.0
            else:
                score_corr = None

            # Cluster overlap
            cluster_a = set()
            cluster_b = set()
            for sk in set_a:
                row = conn.execute(
                    """SELECT cluster_id FROM feature_image_cluster
                        WHERE image_sk = ? AND cluster_type = 'visual' LIMIT 1""",
                    [sk],
                ).fetchone()
                if row:
                    cluster_a.add(row[0])
            for sk in set_b:
                row = conn.execute(
                    """SELECT cluster_id FROM feature_image_cluster
                        WHERE image_sk = ? AND cluster_type = 'visual' LIMIT 1""",
                    [sk],
                ).fetchone()
                if row:
                    cluster_b.add(row[0])

            results.append(
                {
                    "scenario_id": scenario_id,
                    "block_a": block_a,
                    "block_b": block_b,
                    "jaccard_top_n": round(jaccard, 4),
                    "cosine_similarity": round(cosine, 4),
                    "score_correlation": round(score_corr, 4) if score_corr is not None else None,
                    "top_image_overlap_count": intersection,
                    "top_cluster_overlap_count": len(cluster_a & cluster_b),
                }
            )

    return results


def compute_score_impact(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
    top_n: int = 100,
) -> list[dict]:
    """Compute score impact: how much each block changes image rankings.

    Compares selection rates with the block vs global selection rates.
    """
    # Global selection rate per image
    global_rates = conn.execute(
        """
        SELECT image_sk,
               sum(CASE WHEN was_selected THEN 1 ELSE 0 END)::DOUBLE / count(*) as rate
        FROM fact_batch_ballot_image
        WHERE synthetic_flag = true
        GROUP BY image_sk
        """
    ).fetchall()
    global_map = {int(r[0]): r[1] for r in global_rates}

    # Rank globally
    global_ranked = sorted(global_map.items(), key=lambda x: -x[1])
    global_rank = {sk: rank + 1 for rank, (sk, _) in enumerate(global_ranked)}

    # Per-block selection rates
    block_rates = conn.execute(
        """
        SELECT sva.block_id, bbi.image_sk,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END)::DOUBLE / count(*) as rate
        FROM fact_batch_ballot_image bbi
        JOIN synthetic_voter_block_assignment sva
            ON bbi.voter_sk = sva.voter_sk AND sva.scenario_id = ?
        WHERE bbi.synthetic_flag = true
        GROUP BY sva.block_id, bbi.image_sk
        """,
        [scenario_id],
    ).fetchall()

    # Group by block
    block_data: dict[str, dict[int, float]] = {}
    for block_id, image_sk, rate in block_rates:
        image_sk = int(image_sk)
        if block_id not in block_data:
            block_data[block_id] = {}
        block_data[block_id][image_sk] = rate

    results = []
    for block_id, rates in block_data.items():
        # Rank within block
        ranked = sorted(rates.items(), key=lambda x: -x[1])
        block_rank = {sk: rank + 1 for rank, (sk, _) in enumerate(ranked)}

        # Get top-N by absolute score delta
        deltas = []
        for sk, block_rate in rates.items():
            global_rate = global_map.get(sk, 0)
            delta = block_rate - global_rate
            deltas.append((sk, block_rate, global_rate, delta))

        deltas.sort(key=lambda x: -abs(x[3]))

        for sk, block_rate, global_rate, delta in deltas[:top_n]:
            r_with = block_rank.get(sk, len(block_rank))
            r_without = global_rank.get(sk, len(global_rank))
            results.append(
                {
                    "scenario_id": scenario_id,
                    "block_id": block_id,
                    "image_sk": sk,
                    "score_with_block": round(block_rate, 6),
                    "score_without_block": round(global_rate, 6),
                    "score_delta": round(delta, 6),
                    "rank_with_block": r_with,
                    "rank_without_block": r_without,
                    "rank_delta": r_without - r_with,
                    "block_influence_score": round(abs(delta), 6),
                }
            )

    return results


def compute_calendar_impact(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
) -> dict:
    """Compute how voting blocks change the calendar candidate set.

    Compares the top-13 images with all voters vs without block voters.
    """
    # Top 13 with all voters (global)
    global_top = conn.execute(
        """
        SELECT image_sk,
               sum(CASE WHEN was_selected THEN 1 ELSE 0 END)::DOUBLE / count(*) as rate
        FROM fact_batch_ballot_image
        WHERE synthetic_flag = true
        GROUP BY image_sk
        ORDER BY rate DESC
        LIMIT 13
        """
    ).fetchall()
    global_set = {int(r[0]) for r in global_top}
    global_cover = int(global_top[0][0]) if global_top else None

    # Top 13 with block voters only
    block_top = conn.execute(
        """
        SELECT bbi.image_sk,
               sum(CASE WHEN bbi.was_selected THEN 1 ELSE 0 END)::DOUBLE / count(*) as rate
        FROM fact_batch_ballot_image bbi
        JOIN synthetic_voter_block_assignment sva
            ON bbi.voter_sk = sva.voter_sk AND sva.scenario_id = ?
        WHERE bbi.synthetic_flag = true
        GROUP BY bbi.image_sk
        ORDER BY rate DESC
        LIMIT 13
        """,
        [scenario_id],
    ).fetchall()
    block_set = {int(r[0]) for r in block_top}
    block_cover = int(block_top[0][0]) if block_top else None

    changed_count = len(block_set.symmetric_difference(global_set))
    cover_changed = block_cover != global_cover

    return {
        "scenario_id": scenario_id,
        "selected_images_with_json": json.dumps(sorted(block_set)),
        "selected_images_without_json": json.dumps(sorted(global_set)),
        "cover_image_with": block_cover,
        "cover_image_without": global_cover,
        "changed_month_count": changed_count,
        "changed_cover_flag": cover_changed,
        "diversity_score_delta": None,
        "attribute_distribution_delta_json": None,
        "cluster_distribution_delta_json": None,
    }


def compute_detection_status(
    attribute_lift: list[dict],
    block_config_rules: dict[str, list[str]],
) -> dict[str, dict]:
    """Classify detection status per block based on attribute lift results.

    block_config_rules: {block_id: [all_of attribute codes]}
    Returns {block_id: {status, strength, primary_evidence}}.
    """
    results = {}
    for block_id, target_attrs in block_config_rules.items():
        if not target_attrs:
            results[block_id] = {
                "status": "not_applicable",
                "strength": 0.0,
                "primary_evidence": "neutral block",
            }
            continue

        # Find lifts for target attributes
        block_lifts = [r for r in attribute_lift if r["block_id"] == block_id and r["attribute_code"] in target_attrs]

        if not block_lifts:
            results[block_id] = {
                "status": "not_detected",
                "strength": 0.0,
                "primary_evidence": "no lift data for target attributes",
            }
            continue

        avg_lift = np.mean([r["lift"] for r in block_lifts])
        max_lift = max(r["lift"] for r in block_lifts)
        max_attr = max(block_lifts, key=lambda r: r["lift"])["attribute_code"]

        if avg_lift >= 2.0:
            status = "detected"
        elif avg_lift >= 1.3:
            status = "partially_detected"
        elif avg_lift >= 1.1:
            status = "inconclusive"
        else:
            status = "not_detected"

        results[block_id] = {
            "status": status,
            "strength": round(avg_lift, 4),
            "primary_evidence": f"{max_attr} lift={max_lift:.2f}x",
        }

    return results


def write_block_stats(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
    *,
    attribute_lift: list[dict],
    cluster_lift: list[dict],
    similarity: list[dict],
    score_impact: list[dict],
    calendar_impact: dict,
    detection: dict[str, dict],
) -> dict[str, int]:
    """Write all block-aware statistics to mart tables. Returns row counts."""
    counts = {}

    # Attribute lift
    conn.execute(
        "DELETE FROM mart_voting_block_attribute_lift WHERE scenario_id = ?",
        [scenario_id],
    )
    for r in attribute_lift:
        conn.execute(
            """INSERT INTO mart_voting_block_attribute_lift
               (scenario_id, block_id, attribute_code,
                block_selection_rate, global_selection_rate, lift, odds_ratio,
                selected_count, exposed_count,
                confidence_interval_low, confidence_interval_high)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                r["scenario_id"],
                r["block_id"],
                r["attribute_code"],
                r["block_selection_rate"],
                r["global_selection_rate"],
                r["lift"],
                r["odds_ratio"],
                r["selected_count"],
                r["exposed_count"],
                r["confidence_interval_low"],
                r["confidence_interval_high"],
            ],
        )
    counts["attribute_lift"] = len(attribute_lift)

    # Cluster lift
    conn.execute(
        "DELETE FROM mart_voting_block_cluster_lift WHERE scenario_id = ?",
        [scenario_id],
    )
    for r in cluster_lift:
        conn.execute(
            """INSERT INTO mart_voting_block_cluster_lift
               (scenario_id, block_id, cluster_id, cluster_label,
                block_selection_rate, global_selection_rate, lift,
                chi_square_contribution, selected_count, expected_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                r["scenario_id"],
                r["block_id"],
                r["cluster_id"],
                r["cluster_label"],
                r["block_selection_rate"],
                r["global_selection_rate"],
                r["lift"],
                r["chi_square_contribution"],
                r["selected_count"],
                r["expected_count"],
            ],
        )
    counts["cluster_lift"] = len(cluster_lift)

    # Similarity
    conn.execute(
        "DELETE FROM mart_voting_block_similarity WHERE scenario_id = ?",
        [scenario_id],
    )
    for r in similarity:
        conn.execute(
            """INSERT INTO mart_voting_block_similarity
               (scenario_id, block_a, block_b,
                jaccard_top_n, cosine_similarity, score_correlation,
                top_image_overlap_count, top_cluster_overlap_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                r["scenario_id"],
                r["block_a"],
                r["block_b"],
                r["jaccard_top_n"],
                r["cosine_similarity"],
                r["score_correlation"],
                r["top_image_overlap_count"],
                r["top_cluster_overlap_count"],
            ],
        )
    counts["similarity"] = len(similarity)

    # Score impact (top rows only)
    conn.execute(
        "DELETE FROM mart_voting_block_score_impact WHERE scenario_id = ?",
        [scenario_id],
    )
    for r in score_impact:
        conn.execute(
            """INSERT INTO mart_voting_block_score_impact
               (scenario_id, block_id, image_sk,
                score_with_block, score_without_block, score_delta,
                rank_with_block, rank_without_block, rank_delta,
                block_influence_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                r["scenario_id"],
                r["block_id"],
                r["image_sk"],
                r["score_with_block"],
                r["score_without_block"],
                r["score_delta"],
                r["rank_with_block"],
                r["rank_without_block"],
                r["rank_delta"],
                r["block_influence_score"],
            ],
        )
    counts["score_impact"] = len(score_impact)

    # Calendar impact
    conn.execute(
        "DELETE FROM mart_voting_block_calendar_impact WHERE scenario_id = ?",
        [scenario_id],
    )
    conn.execute(
        """INSERT INTO mart_voting_block_calendar_impact
           (scenario_id, selected_images_with_json, selected_images_without_json,
            cover_image_with, cover_image_without,
            changed_month_count, changed_cover_flag,
            diversity_score_delta, attribute_distribution_delta_json,
            cluster_distribution_delta_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            calendar_impact["scenario_id"],
            calendar_impact["selected_images_with_json"],
            calendar_impact["selected_images_without_json"],
            calendar_impact["cover_image_with"],
            calendar_impact["cover_image_without"],
            calendar_impact["changed_month_count"],
            calendar_impact["changed_cover_flag"],
            calendar_impact["diversity_score_delta"],
            calendar_impact["attribute_distribution_delta_json"],
            calendar_impact["cluster_distribution_delta_json"],
        ],
    )
    counts["calendar_impact"] = 1

    # Block summary
    conn.execute(
        "DELETE FROM mart_voting_block_summary WHERE scenario_id = ?",
        [scenario_id],
    )
    blocks = conn.execute(
        "SELECT block_id, block_label, voter_count, votes_per_voter FROM dim_voting_block WHERE scenario_id = ?",
        [scenario_id],
    ).fetchall()
    for block_id, _label, voter_count, votes_per_voter in blocks:
        det = detection.get(block_id, {})
        conn.execute(
            """INSERT INTO mart_voting_block_summary
               (scenario_id, block_id, voter_count, vote_count, detection_status)
               VALUES (?, ?, ?, ?, ?)""",
            [scenario_id, block_id, voter_count, voter_count * votes_per_voter, det.get("status")],
        )
    counts["block_summary"] = len(blocks)

    logger.info(f"Block stats written for {scenario_id}: {counts}")
    return counts


def run_block_analysis(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
) -> dict:
    """Orchestrator: run all block-aware analyses and persist results."""
    logger.info(f"Running block analysis for scenario {scenario_id!r}")

    attr_lift = compute_attribute_lift(conn, scenario_id)
    clust_lift = compute_cluster_lift(conn, scenario_id)
    sim = compute_block_similarity(conn, scenario_id)
    impact = compute_score_impact(conn, scenario_id)
    cal_impact = compute_calendar_impact(conn, scenario_id)

    # Build detection config from block rules
    block_rules = {}
    rules = conn.execute(
        "SELECT block_id, attribute_code FROM voting_block_rule WHERE scenario_id = ? AND rule_type = 'all_of'",
        [scenario_id],
    ).fetchall()
    for block_id, code in rules:
        if block_id not in block_rules:
            block_rules[block_id] = []
        block_rules[block_id].append(code)
    # Add neutral blocks
    all_blocks = conn.execute(
        "SELECT block_id FROM dim_voting_block WHERE scenario_id = ?",
        [scenario_id],
    ).fetchall()
    for (block_id,) in all_blocks:
        if block_id not in block_rules:
            block_rules[block_id] = []

    detection = compute_detection_status(attr_lift, block_rules)

    counts = write_block_stats(
        conn,
        scenario_id,
        attribute_lift=attr_lift,
        cluster_lift=clust_lift,
        similarity=sim,
        score_impact=impact,
        calendar_impact=cal_impact,
        detection=detection,
    )

    return {
        "scenario_id": scenario_id,
        "counts": counts,
        "detection": detection,
    }
