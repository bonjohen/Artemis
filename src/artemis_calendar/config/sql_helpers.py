"""Reusable SQL subquery fragments for latest-run resolution.

These inline subqueries appear in 7+ modules. Centralizing them here ensures
schema changes (e.g., adding a run_status filter) propagate everywhere.
"""

LATEST_SCORE_RUN = """(
    SELECT score_run_id FROM mart_image_preference_score
    ORDER BY created_at DESC LIMIT 1
)"""

LATEST_VISUAL_CLUSTER_RUN = """(
    SELECT cluster_run_id FROM feature_image_cluster
    WHERE cluster_type = 'visual'
    ORDER BY created_at DESC LIMIT 1
)"""

# Filter to exclude dedup-suppressed and near-black images.
# Requires dim_image as 'd' and LEFT JOIN feature_image_visual as 'v'.
# Excludes: (1) non-master dedup members, (2) images >= 92% dark pixels.
ACTIVE_IMAGE_FILTER = (
    "COALESCE(d.is_suppressed, false) = false"
    " AND d.image_sk NOT IN ("
    "    SELECT image_sk FROM dedup_image_member WHERE is_master = false"
    " )"
    " AND COALESCE(v.dark_pixel_ratio, 0) < 0.92"
)
