"""Inter-rater reliability: Krippendorff's alpha from coincidence matrix."""

from __future__ import annotations

import duckdb
import numpy as np

from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.models.reliability")


def compute_reliability(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, dict]:
    """Compute inter-rater reliability metrics for each vote mode.

    Returns dict keyed by vote_mode with keys:
        image_count, voter_count, rating_density, krippendorff_alpha,
        fleiss_kappa, kendall_w, spearman_mean, method_notes
    """
    results = {}

    # Batch voting reliability
    batch_result = _batch_reliability(conn)
    if batch_result:
        results["batch_pick_5_of_50"] = batch_result

    # Category ranking reliability
    category_result = _category_reliability(conn)
    if category_result:
        results["category_top_3"] = category_result

    return results


def _batch_reliability(conn: duckdb.DuckDBPyConnection) -> dict | None:
    """Compute Krippendorff's alpha for batch ballot data.

    Rating matrix: voters x images, values = 1 (selected) / 0 (shown, not selected) / NaN (not shown).
    """
    rows = conn.execute(
        """
        SELECT voter_sk, image_sk, was_selected
        FROM fact_batch_ballot_image
        ORDER BY voter_sk, image_sk
        """
    ).fetchall()

    if not rows:
        return None

    # Build voter-image rating dict
    ratings: dict[int, dict[int, int]] = {}
    for voter_sk, image_sk, was_selected in rows:
        voter_sk = int(voter_sk)
        image_sk = int(image_sk)
        if voter_sk not in ratings:
            ratings[voter_sk] = {}
        ratings[voter_sk][image_sk] = 1 if was_selected else 0

    voters = sorted(ratings.keys())
    images = sorted({img for v in ratings.values() for img in v})

    # Build matrix (voters x images), NaN for missing
    matrix = np.full((len(voters), len(images)), np.nan)
    voter_idx = {v: i for i, v in enumerate(voters)}
    image_idx = {img: i for i, img in enumerate(images)}

    for voter_sk, img_ratings in ratings.items():
        vi = voter_idx[voter_sk]
        for image_sk, val in img_ratings.items():
            matrix[vi, image_idx[image_sk]] = val

    # Density: fraction of non-NaN cells
    total_cells = matrix.size
    filled_cells = int(np.count_nonzero(~np.isnan(matrix)))
    density = filled_cells / total_cells if total_cells > 0 else 0.0

    alpha = krippendorff_alpha_nominal(matrix)

    return {
        "image_count": len(images),
        "voter_count": len(voters),
        "rating_density": density,
        "krippendorff_alpha": alpha,
        "fleiss_kappa": None,  # Requires complete data
        "kendall_w": None,  # Requires complete rankings
        "spearman_mean": None,
        "method_notes": (
            f"Krippendorff's alpha (nominal) on {len(voters)}x{len(images)} matrix, "
            f"density={density:.4f}. Fleiss/Kendall skipped (incomplete data)."
        ),
    }


def _category_reliability(conn: duckdb.DuckDBPyConnection) -> dict | None:
    """Compute Krippendorff's alpha for category ranking data.

    Rating matrix: voters x images, values = Borda score (3/2/1) or NaN.
    """
    rows = conn.execute(
        """
        SELECT voter_sk, image_sk, borda_score
        FROM fact_category_ranking_image
        ORDER BY voter_sk, image_sk
        """
    ).fetchall()

    if not rows:
        return None

    ratings: dict[int, dict[int, float]] = {}
    for voter_sk, image_sk, borda in rows:
        voter_sk = int(voter_sk)
        image_sk = int(image_sk)
        if voter_sk not in ratings:
            ratings[voter_sk] = {}
        ratings[voter_sk][image_sk] = float(borda)

    voters = sorted(ratings.keys())
    images = sorted({img for v in ratings.values() for img in v})

    matrix = np.full((len(voters), len(images)), np.nan)
    voter_idx = {v: i for i, v in enumerate(voters)}
    image_idx = {img: i for i, img in enumerate(images)}

    for voter_sk, img_ratings in ratings.items():
        vi = voter_idx[voter_sk]
        for image_sk, val in img_ratings.items():
            matrix[vi, image_idx[image_sk]] = val

    total_cells = matrix.size
    filled_cells = int(np.count_nonzero(~np.isnan(matrix)))
    density = filled_cells / total_cells if total_cells > 0 else 0.0

    alpha = krippendorff_alpha_ordinal(matrix)

    return {
        "image_count": len(images),
        "voter_count": len(voters),
        "rating_density": density,
        "krippendorff_alpha": alpha,
        "fleiss_kappa": None,
        "kendall_w": None,
        "spearman_mean": None,
        "method_notes": (
            f"Krippendorff's alpha (ordinal) on {len(voters)}x{len(images)} matrix, "
            f"density={density:.4f}. Category ranking Borda scores (3/2/1)."
        ),
    }


def krippendorff_alpha_nominal(matrix: np.ndarray) -> float | None:
    """Compute Krippendorff's alpha for nominal data from a raters x items matrix.

    NaN entries are treated as missing. Uses the coincidence matrix formulation
    which handles incomplete data natively.
    """
    return _krippendorff_alpha(matrix, metric="nominal")


def krippendorff_alpha_ordinal(matrix: np.ndarray) -> float | None:
    """Compute Krippendorff's alpha for ordinal data."""
    return _krippendorff_alpha(matrix, metric="ordinal")


def _krippendorff_alpha(matrix: np.ndarray, metric: str = "nominal") -> float | None:
    """Core Krippendorff's alpha computation via coincidence matrix.

    Args:
        matrix: (raters x items) with NaN for missing values.
        metric: "nominal" or "ordinal".

    Returns alpha value or None if insufficient data.
    """
    n_raters, n_items = matrix.shape

    # Collect unique non-NaN values
    all_values = matrix[~np.isnan(matrix)]
    if len(all_values) == 0:
        return None
    categories = np.unique(all_values)
    n_cats = len(categories)
    if n_cats < 2:
        return None  # Perfect agreement or degenerate

    cat_idx = {v: i for i, v in enumerate(categories)}

    # Build coincidence matrix
    coincidence = np.zeros((n_cats, n_cats))
    for j in range(n_items):
        col = matrix[:, j]
        valid = col[~np.isnan(col)]
        m_u = len(valid)
        if m_u < 2:
            continue
        # For each pair of raters who both rated this item
        for a_idx in range(len(valid)):
            for b_idx in range(len(valid)):
                if a_idx == b_idx:
                    continue
                c = cat_idx[valid[a_idx]]
                k = cat_idx[valid[b_idx]]
                coincidence[c, k] += 1.0 / (m_u - 1)

    # Marginals
    n_total = coincidence.sum()
    if n_total == 0:
        return None
    marginals = coincidence.sum(axis=1)

    # Observed disagreement
    if metric == "nominal":
        d_o = 1.0 - np.trace(coincidence) / n_total
    elif metric == "ordinal":
        # Ordinal metric: squared difference weighted by cumulative frequencies
        d_o = 0.0
        d_e = 0.0
        for c in range(n_cats):
            for k in range(n_cats):
                if c == k:
                    continue
                # Ordinal distance: number of categories between c and k
                n_ck = sum(marginals[min(c, k) : max(c, k) + 1])
                dist_sq = (n_ck - (marginals[c] + marginals[k]) / 2) ** 2
                d_o += coincidence[c, k] * dist_sq
                d_e += marginals[c] * marginals[k] * dist_sq
        if d_e == 0:
            return None
        d_o /= n_total
        d_e /= n_total * (n_total - 1)
        return 1.0 - d_o / d_e if d_e != 0 else None
    else:
        return None

    # Expected disagreement (nominal)
    d_e = 1.0 - np.sum(marginals * (marginals - 1)) / (n_total * (n_total - 1))

    if d_e == 0:
        return 1.0  # Perfect agreement
    return 1.0 - d_o / d_e
