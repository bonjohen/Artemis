"""Generate cluster labels from dominant image attributes and captions."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from artemis_calendar.config.settings import OUTPUT_ROOT
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.vision.cluster_labels")

REVIEW_OUTPUT_DIR = OUTPUT_ROOT / "review"


def _get_cluster_dominant_attributes(
    conn: duckdb.DuckDBPyConnection,
    cluster_run_id: str,
    cluster_type: str,
    cluster_id: int,
    top_n: int = 5,
) -> list[dict]:
    """Get the most common accepted attributes for images in a cluster."""
    rows = conn.execute(
        """
        SELECT fa.attribute_code, count(*) as cnt,
               avg(fa.confidence_score) as avg_conf
        FROM feature_image_cluster fic
        JOIN feature_image_attribute fa ON fic.image_sk = fa.image_sk
        WHERE fic.cluster_run_id = ?
          AND fic.cluster_type = ?
          AND fic.cluster_id = ?
          AND fa.is_accepted = true
          AND fa.label_source != 'derived_rule'
        GROUP BY fa.attribute_code
        ORDER BY cnt DESC
        LIMIT ?
        """,
        [cluster_run_id, cluster_type, cluster_id, top_n],
    ).fetchall()
    return [
        {"code": r[0], "count": r[1], "avg_confidence": round(r[2], 3)}
        for r in rows
    ]


def _get_cluster_representative_images(
    conn: duckdb.DuckDBPyConnection,
    cluster_run_id: str,
    cluster_type: str,
    cluster_id: int,
    top_n: int = 5,
) -> list[dict]:
    """Get images closest to the cluster centroid."""
    rows = conn.execute(
        """
        SELECT fic.image_sk, di.source_image_id, fic.distance_to_centroid
        FROM feature_image_cluster fic
        JOIN dim_image di ON fic.image_sk = di.image_sk
        WHERE fic.cluster_run_id = ?
          AND fic.cluster_type = ?
          AND fic.cluster_id = ?
          AND fic.distance_to_centroid IS NOT NULL
        ORDER BY fic.distance_to_centroid ASC
        LIMIT ?
        """,
        [cluster_run_id, cluster_type, cluster_id, top_n],
    ).fetchall()
    return [
        {
            "image_sk": r[0],
            "source_image_id": r[1],
            "distance": round(r[2], 4) if r[2] is not None else None,
        }
        for r in rows
    ]


def _get_cluster_outlier_images(
    conn: duckdb.DuckDBPyConnection,
    cluster_run_id: str,
    cluster_type: str,
    cluster_id: int,
    top_n: int = 3,
) -> list[dict]:
    """Get images farthest from the cluster centroid."""
    rows = conn.execute(
        """
        SELECT fic.image_sk, di.source_image_id, fic.distance_to_centroid
        FROM feature_image_cluster fic
        JOIN dim_image di ON fic.image_sk = di.image_sk
        WHERE fic.cluster_run_id = ?
          AND fic.cluster_type = ?
          AND fic.cluster_id = ?
          AND fic.distance_to_centroid IS NOT NULL
        ORDER BY fic.distance_to_centroid DESC
        LIMIT ?
        """,
        [cluster_run_id, cluster_type, cluster_id, top_n],
    ).fetchall()
    return [
        {
            "image_sk": r[0],
            "source_image_id": r[1],
            "distance": round(r[2], 4) if r[2] is not None else None,
        }
        for r in rows
    ]


def _generate_label(dominant_attrs: list[dict]) -> str:
    """Generate a human-readable cluster label from dominant attributes."""
    if not dominant_attrs:
        return "Uncategorized"

    # Take top 3 attributes and join them
    codes = [a["code"].replace("_", " ").title() for a in dominant_attrs[:3]]
    if len(codes) == 1:
        return codes[0]
    if len(codes) == 2:
        return f"{codes[0]} and {codes[1]}"
    return f"{codes[0]}, {codes[1]}, and {codes[2]}"


def label_clusters(
    conn: duckdb.DuckDBPyConnection,
    cluster_run_id: str | None = None,
    cluster_type: str = "visual",
) -> int:
    """Generate and store labels for clusters.

    If cluster_run_id is None, uses the most recent run.
    Returns number of clusters labeled.
    """
    if cluster_run_id is None:
        row = conn.execute(
            "SELECT DISTINCT cluster_run_id FROM feature_image_cluster ORDER BY cluster_run_id DESC LIMIT 1"
        ).fetchone()
        if not row:
            logger.warning("No cluster runs found")
            return 0
        cluster_run_id = row[0]

    # Get all cluster IDs for this run and type
    cluster_rows = conn.execute(
        """
        SELECT DISTINCT cluster_id, count(*) as size
        FROM feature_image_cluster
        WHERE cluster_run_id = ? AND cluster_type = ?
        GROUP BY cluster_id
        ORDER BY cluster_id
        """,
        [cluster_run_id, cluster_type],
    ).fetchall()

    if not cluster_rows:
        logger.warning(f"No clusters found for run={cluster_run_id}, type={cluster_type}")
        return 0

    count = 0
    for cluster_id, size in cluster_rows:
        dominant = _get_cluster_dominant_attributes(
            conn, cluster_run_id, cluster_type, cluster_id
        )
        label = _generate_label(dominant)

        # Update cluster_label in feature_image_cluster
        conn.execute(
            """
            UPDATE feature_image_cluster
            SET cluster_label = ?
            WHERE cluster_run_id = ? AND cluster_type = ? AND cluster_id = ?
            """,
            [label, cluster_run_id, cluster_type, cluster_id],
        )

        # Also update mart_image_cluster_summary if it exists
        conn.execute(
            """
            UPDATE mart_image_cluster_summary
            SET cluster_label = ?
            WHERE cluster_run_id = ? AND cluster_type = ? AND cluster_id = ?
            """,
            [label, cluster_run_id, cluster_type, cluster_id],
        )

        count += 1
        logger.debug(f"Cluster {cluster_id} ({size} images): {label}")

    logger.info(f"Labeled {count} {cluster_type} clusters for run {cluster_run_id}")
    return count


def export_cluster_review(
    conn: duckdb.DuckDBPyConnection,
    cluster_run_id: str | None = None,
    cluster_type: str = "visual",
    output_dir: Path | None = None,
) -> dict:
    """Export cluster review files (JSON and Markdown).

    Returns summary dict with output paths.
    """
    odir = output_dir or REVIEW_OUTPUT_DIR
    odir.mkdir(parents=True, exist_ok=True)

    if cluster_run_id is None:
        row = conn.execute(
            "SELECT DISTINCT cluster_run_id FROM feature_image_cluster ORDER BY cluster_run_id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return {"error": "No cluster runs found"}
        cluster_run_id = row[0]

    cluster_rows = conn.execute(
        """
        SELECT DISTINCT cluster_id, cluster_label, count(*) as size
        FROM feature_image_cluster
        WHERE cluster_run_id = ? AND cluster_type = ?
        GROUP BY cluster_id, cluster_label
        ORDER BY cluster_id
        """,
        [cluster_run_id, cluster_type],
    ).fetchall()

    clusters = []
    for cluster_id, label, size in cluster_rows:
        dominant = _get_cluster_dominant_attributes(
            conn, cluster_run_id, cluster_type, cluster_id
        )
        representatives = _get_cluster_representative_images(
            conn, cluster_run_id, cluster_type, cluster_id
        )
        outliers = _get_cluster_outlier_images(
            conn, cluster_run_id, cluster_type, cluster_id
        )

        clusters.append({
            "cluster_id": cluster_id,
            "label": label or "Unlabeled",
            "image_count": size,
            "dominant_attributes": dominant,
            "representative_images": representatives,
            "outlier_images": outliers,
        })

    # Write JSON
    json_path = odir / "cluster_review.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "cluster_run_id": cluster_run_id,
            "cluster_type": cluster_type,
            "cluster_count": len(clusters),
            "clusters": clusters,
        }, f, indent=2)

    # Write Markdown
    md_path = odir / "cluster_review.md"
    lines = [
        f"# Cluster Review — {cluster_type}",
        f"\n**Run ID:** {cluster_run_id}",
        f"**Clusters:** {len(clusters)}",
        f"**Total images:** {sum(c['image_count'] for c in clusters)}",
        "",
    ]
    for c in clusters:
        lines.append(f"## Cluster {c['cluster_id']}: {c['label']}")
        lines.append(f"\n**Images:** {c['image_count']}")
        if c["dominant_attributes"]:
            lines.append("\n**Dominant attributes:**")
            for a in c["dominant_attributes"]:
                lines.append(f"- {a['code']} (count={a['count']}, avg_conf={a['avg_confidence']})")
        if c["representative_images"]:
            lines.append("\n**Representative images:**")
            for img in c["representative_images"]:
                lines.append(f"- {img['source_image_id']} (dist={img['distance']})")
        if c["outlier_images"]:
            lines.append("\n**Outlier images:**")
            for img in c["outlier_images"]:
                lines.append(f"- {img['source_image_id']} (dist={img['distance']})")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Cluster review exported: {json_path}, {md_path}")
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
        "cluster_count": len(clusters),
    }
