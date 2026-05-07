"""Month assignment via Hungarian algorithm."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from artemis_calendar.observe.logging import get_logger
from artemis_calendar.optimize.month_fit import CALENDAR_MONTHS

logger = get_logger("artemis.optimize.assignment")


def assign_months(
    selected_sks: list[int],
    month_fit: dict[int, np.ndarray],
) -> list[tuple[int, int, str]]:
    """Assign 13 selected images to 13 calendar months optimally.

    Uses the Hungarian algorithm to maximize total month-fit.

    Returns list of (image_sk, sequence_number, month_label) tuples,
    sorted by sequence_number.
    """
    n = len(selected_sks)
    if n != 13:
        logger.warning(f"Expected 13 images, got {n}. Assigning what we have.")

    # Build cost matrix (negate fit for minimization)
    cost = np.zeros((n, 13), dtype=np.float64)
    for i, sk in enumerate(selected_sks):
        mf = month_fit.get(sk)
        if mf is not None:
            cost[i, :] = -mf[:13]

    # Solve assignment
    row_ind, col_ind = linear_sum_assignment(cost)

    assignments = []
    for r, c in zip(row_ind, col_ind, strict=True):
        sk = selected_sks[r]
        month = CALENDAR_MONTHS[c]
        assignments.append((sk, month["sequence"], month["label"]))

    assignments.sort(key=lambda x: x[1])

    total_fit = -cost[row_ind, col_ind].sum()
    logger.info(f"Assigned {len(assignments)} images to months (total fit: {total_fit:.3f})")
    return assignments
