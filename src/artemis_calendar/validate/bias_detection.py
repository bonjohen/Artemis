"""S3: Bias detection validation — detect planted biases in synthetic vote data."""

from __future__ import annotations

import duckdb
import numpy as np
from scipy import stats

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.validate.bias")


def detect_position_bias(conn: duckdb.DuckDBPyConnection) -> dict:
    """Detect display-position bias in batch ballots and pairwise left/right bias.

    Batch: chi-squared test of independence between position group and selection.
    Pairwise: binomial test of left-image win rate vs 0.5.
    """
    result = {
        "position_bias_coeff": None,
        "position_bias_pvalue": None,
        "position_bias_detected": False,
        "pairwise_left_win_rate": None,
        "pairwise_left_pvalue": None,
    }

    # Batch position bias: split positions into thirds, test independence
    rows = conn.execute(
        """
        SELECT display_position, was_selected
        FROM fact_batch_ballot_image
        WHERE synthetic_flag = true AND display_position IS NOT NULL
        """
    ).fetchall()

    if len(rows) >= 10:
        positions = np.array([r[0] for r in rows])
        selected = np.array([1 if r[1] else 0 for r in rows])

        # Split into thirds: early (0-16), middle (17-33), late (34-49)
        groups = np.where(positions < 17, 0, np.where(positions < 34, 1, 2))

        # Build contingency table: groups x selected/not-selected
        contingency = np.zeros((3, 2), dtype=int)
        for g in range(3):
            mask = groups == g
            contingency[g, 1] = int(selected[mask].sum())
            contingency[g, 0] = int(mask.sum()) - contingency[g, 1]

        if contingency.min() >= 0 and contingency.sum() > 0:
            chi2, pvalue, _, _ = stats.chi2_contingency(contingency)
            # Effect size: selection rate difference between early and late thirds
            early_rate = contingency[0, 1] / max(1, contingency[0].sum())
            late_rate = contingency[2, 1] / max(1, contingency[2].sum())
            coeff = early_rate - late_rate

            result["position_bias_coeff"] = float(coeff)
            result["position_bias_pvalue"] = float(pvalue)
            result["position_bias_detected"] = bool(pvalue < 0.05)

            logger.info(
                f"Position bias: early_rate={early_rate:.4f}, late_rate={late_rate:.4f}, "
                f"chi2={chi2:.2f}, p={pvalue:.4f}, detected={pvalue < 0.05}"
            )

    # Pairwise left/right bias
    pairwise_rows = conn.execute(
        """
        SELECT winner_image_sk, left_image_sk
        FROM fact_pairwise_vote
        WHERE synthetic_flag = true AND left_image_sk IS NOT NULL
        """
    ).fetchall()

    if pairwise_rows:
        left_wins = sum(1 for r in pairwise_rows if r[0] == r[1])
        total = len(pairwise_rows)
        left_rate = left_wins / total

        binom_result = stats.binomtest(left_wins, total, 0.5)
        result["pairwise_left_win_rate"] = float(left_rate)
        result["pairwise_left_pvalue"] = float(binom_result.pvalue)

        logger.info(f"Pairwise left-win rate: {left_rate:.4f} ({left_wins}/{total}), p={binom_result.pvalue:.4f}")

    return result


def detect_cluster_bias(conn: duckdb.DuckDBPyConnection) -> dict:
    """Detect over-selection of specific visual clusters.

    Chi-squared goodness-of-fit: observed selection counts vs expected (proportional to cluster size).
    """
    result = {
        "cluster_bias_chi2": None,
        "cluster_bias_pvalue": None,
        "top_overselected_clusters": [],
    }

    # Get cluster sizes (expected proportions)
    cluster_sizes = conn.execute(
        """
        SELECT cluster_label, count(*) as size
        FROM feature_image_cluster
        WHERE cluster_type = 'visual'
        GROUP BY cluster_label
        ORDER BY cluster_label
        """
    ).fetchall()

    if not cluster_sizes:
        logger.warning("No visual cluster data found")
        return result

    cluster_labels = [r[0] for r in cluster_sizes]
    sizes = np.array([r[1] for r in cluster_sizes], dtype=float)
    total_images = sizes.sum()

    # Get observed selection counts per cluster
    observed_rows = conn.execute(
        """
        SELECT fic.cluster_label, count(*) as selected_count
        FROM fact_batch_ballot_image bbi
        JOIN feature_image_cluster fic
            ON bbi.image_sk = fic.image_sk AND fic.cluster_type = 'visual'
        WHERE bbi.synthetic_flag = true AND bbi.was_selected = true
        GROUP BY fic.cluster_label
        ORDER BY fic.cluster_label
        """
    ).fetchall()

    if not observed_rows:
        logger.warning("No selected ballot images found")
        return result

    # Build observed array aligned with cluster_labels
    observed_map = {r[0]: r[1] for r in observed_rows}
    observed = np.array([observed_map.get(label, 0) for label in cluster_labels], dtype=float)
    total_selected = observed.sum()

    if total_selected == 0:
        return result

    # Expected counts proportional to cluster size
    expected = (sizes / total_images) * total_selected

    # Filter out clusters with expected < 1 to avoid chi-squared instability
    mask = expected >= 1.0
    if mask.sum() < 2:
        logger.warning("Too few clusters with expected >= 1 for chi-squared test")
        return result

    chi2, pvalue = stats.chisquare(observed[mask], expected[mask])
    result["cluster_bias_chi2"] = float(chi2)
    result["cluster_bias_pvalue"] = float(pvalue)

    # Compute lift ratios for reporting
    lift = observed / np.maximum(expected, 1e-10)
    top_indices = np.argsort(lift)[::-1][:3]
    result["top_overselected_clusters"] = [
        {
            "cluster": cluster_labels[i],
            "lift": float(lift[i]),
            "observed": int(observed[i]),
            "expected": float(expected[i]),
        }
        for i in top_indices
        if lift[i] > 1.0
    ]

    logger.info(f"Cluster bias: chi2={chi2:.2f}, p={pvalue:.4f}, top lifts={result['top_overselected_clusters']}")
    return result


def segment_voters(conn: duckdb.DuckDBPyConnection) -> dict:
    """Analyze voter segments by comparing per-voter agreement with population consensus.

    Groups voters by synthetic_profile_code and computes mean agreement per profile.
    """
    result = {
        "voter_segment_count": 0,
        "voter_consensus_std": None,
        "profile_stats": {},
    }

    # Get population top images (most selected across all voters)
    top_images = conn.execute(
        """
        SELECT image_sk, count(*) as sel_count
        FROM fact_batch_ballot_image
        WHERE synthetic_flag = true AND was_selected = true
        GROUP BY image_sk
        ORDER BY sel_count DESC
        LIMIT 50
        """
    ).fetchall()

    if not top_images:
        return result

    population_top = {r[0] for r in top_images}

    # Per-voter selections
    voter_selections = conn.execute(
        """
        SELECT v.voter_sk, v.synthetic_profile_code, bbi.image_sk
        FROM dim_voter v
        JOIN fact_batch_ballot_image bbi ON v.voter_sk = bbi.voter_sk
        WHERE v.synthetic_flag = true AND bbi.was_selected = true
        """
    ).fetchall()

    if not voter_selections:
        return result

    # Build per-voter selection sets
    voter_images: dict[int, set[int]] = {}
    voter_profiles: dict[int, str] = {}
    for voter_sk, profile, image_sk in voter_selections:
        voter_sk = int(voter_sk)
        if voter_sk not in voter_images:
            voter_images[voter_sk] = set()
            voter_profiles[voter_sk] = profile
        voter_images[voter_sk].add(int(image_sk))

    # Compute Jaccard agreement with population top
    agreements: dict[str, list[float]] = {}
    all_agreements = []
    for voter_sk, images in voter_images.items():
        profile = voter_profiles[voter_sk]
        intersection = len(images & population_top)
        union = len(images | population_top)
        jaccard = intersection / union if union > 0 else 0.0
        all_agreements.append(jaccard)
        if profile not in agreements:
            agreements[profile] = []
        agreements[profile].append(jaccard)

    result["voter_segment_count"] = len(agreements)
    result["voter_consensus_std"] = float(np.std(all_agreements)) if all_agreements else None

    for profile, scores in agreements.items():
        result["profile_stats"][profile] = {
            "count": len(scores),
            "mean_agreement": float(np.mean(scores)),
            "std_agreement": float(np.std(scores)),
        }

    logger.info(f"Voter segments: {len(agreements)} profiles, consensus_std={result['voter_consensus_std']:.4f}")
    return result


def compare_scores_to_truth(conn: duckdb.DuckDBPyConnection) -> dict:
    """Spearman rank correlation between computed composite scores and planted ground truth."""
    result = {
        "score_vs_truth_spearman": None,
        "score_vs_truth_pvalue": None,
    }

    rows = conn.execute(
        """
        SELECT m.posterior_mean, s.latent_general_appeal
        FROM mart_image_preference_score m
        JOIN synthetic_image_truth s ON m.image_sk = s.image_sk
        WHERE m.posterior_mean IS NOT NULL AND s.latent_general_appeal IS NOT NULL
        """
    ).fetchall()

    if len(rows) < 3:
        logger.warning(f"Insufficient data for score-truth comparison: {len(rows)} rows")
        return result

    scores = [r[0] for r in rows]
    truth = [r[1] for r in rows]

    rho, pvalue = stats.spearmanr(scores, truth)
    result["score_vs_truth_spearman"] = float(rho)
    result["score_vs_truth_pvalue"] = float(pvalue)

    logger.info(f"Score vs truth: Spearman rho={rho:.4f}, p={pvalue:.6f}")
    return result


def reliability_under_bias(conn: duckdb.DuckDBPyConnection) -> dict:
    """Compare Krippendorff's alpha with and without biased/random voters.

    Recomputes alpha excluding position_biased and random profiles to measure
    how much noise they inject into agreement.
    """
    from artemis_calendar.models.reliability import krippendorff_alpha_nominal

    result = {
        "alpha_all_voters": None,
        "alpha_excluding_biased": None,
        "alpha_delta": None,
    }

    def _build_matrix(conn: duckdb.DuckDBPyConnection, exclude_profiles: tuple = ()) -> np.ndarray | None:
        if exclude_profiles:
            placeholders = ", ".join(["?"] * len(exclude_profiles))
            query = f"""
                SELECT bbi.voter_sk, bbi.image_sk, bbi.was_selected
                FROM fact_batch_ballot_image bbi
                JOIN dim_voter v ON bbi.voter_sk = v.voter_sk
                WHERE bbi.synthetic_flag = true
                  AND v.synthetic_profile_code NOT IN ({placeholders})
                ORDER BY bbi.voter_sk, bbi.image_sk
            """
            rows = conn.execute(query, list(exclude_profiles)).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT voter_sk, image_sk, was_selected
                FROM fact_batch_ballot_image
                WHERE synthetic_flag = true
                ORDER BY voter_sk, image_sk
                """
            ).fetchall()

        if not rows:
            return None

        ratings: dict[int, dict[int, int]] = {}
        for voter_sk, image_sk, was_selected in rows:
            voter_sk, image_sk = int(voter_sk), int(image_sk)
            if voter_sk not in ratings:
                ratings[voter_sk] = {}
            ratings[voter_sk][image_sk] = 1 if was_selected else 0

        voters = sorted(ratings.keys())
        images = sorted({img for v in ratings.values() for img in v})
        matrix = np.full((len(voters), len(images)), np.nan)
        voter_idx = {v: i for i, v in enumerate(voters)}
        image_idx = {img: i for i, img in enumerate(images)}

        for voter_sk, img_ratings in ratings.items():
            for image_sk, val in img_ratings.items():
                matrix[voter_idx[voter_sk], image_idx[image_sk]] = val

        return matrix

    # All voters
    matrix_all = _build_matrix(conn)
    if matrix_all is not None:
        result["alpha_all_voters"] = krippendorff_alpha_nominal(matrix_all)

    # Excluding biased + random
    matrix_clean = _build_matrix(conn, exclude_profiles=("position_biased", "random"))
    if matrix_clean is not None:
        result["alpha_excluding_biased"] = krippendorff_alpha_nominal(matrix_clean)

    if result["alpha_all_voters"] is not None and result["alpha_excluding_biased"] is not None:
        result["alpha_delta"] = result["alpha_excluding_biased"] - result["alpha_all_voters"]

    logger.info(
        f"Reliability: alpha_all={result['alpha_all_voters']}, "
        f"alpha_clean={result['alpha_excluding_biased']}, "
        f"delta={result['alpha_delta']}"
    )
    return result


def run_bias_detection(conn: duckdb.DuckDBPyConnection) -> dict:
    """Orchestrator: run all bias detection analyses and persist results.

    Returns combined report dict.
    """
    from artemis_calendar.observe.run_manifest import generate_run_id
    from artemis_calendar.validate.marts import write_bias_detection

    logger.info("Starting bias detection validation (S3)...")

    position = detect_position_bias(conn)
    cluster = detect_cluster_bias(conn)
    voters = segment_voters(conn)
    scores = compare_scores_to_truth(conn)
    reliability = reliability_under_bias(conn)

    detection_run_id = generate_run_id()
    report = {
        "detection_run_id": detection_run_id,
        **position,
        **{k: v for k, v in cluster.items() if k != "top_overselected_clusters"},
        "voter_segment_count": voters["voter_segment_count"],
        "voter_consensus_std": voters["voter_consensus_std"],
        **scores,
        **reliability,
    }

    write_bias_detection(conn, report)

    # Build summary for logging
    findings = []
    if position["position_bias_detected"]:
        findings.append(f"Position bias detected (p={position['position_bias_pvalue']:.4f})")
    if cluster["cluster_bias_pvalue"] is not None and cluster["cluster_bias_pvalue"] < 0.05:
        findings.append(f"Cluster bias detected (p={cluster['cluster_bias_pvalue']:.4f})")
    if scores["score_vs_truth_spearman"] is not None:
        findings.append(f"Score-truth correlation: rho={scores['score_vs_truth_spearman']:.4f}")
    if reliability["alpha_delta"] is not None:
        findings.append(f"Reliability delta: {reliability['alpha_delta']:+.4f}")

    logger.info(f"Bias detection complete. Findings: {findings}")

    # Include detailed sub-reports for callers
    report["cluster_details"] = cluster.get("top_overselected_clusters", [])
    report["profile_stats"] = voters.get("profile_stats", {})

    return report
