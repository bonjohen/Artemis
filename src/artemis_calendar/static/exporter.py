"""Export block-aware analysis results to static JSON for the public site."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from artemis_calendar.config.settings import PROJECT_ROOT
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.static.exporter")

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "_site_new" / "api"


def _sanitize_no_pii(data: dict | list) -> dict | list:
    """Verify exported data contains no PII fields."""
    forbidden = {"voter_sk", "voter_public_hash", "random_seed", "seed", "config_hash"}
    if isinstance(data, dict):
        for key in list(data.keys()):
            if key in forbidden:
                del data[key]
            elif isinstance(data[key], (dict, list)):
                data[key] = _sanitize_no_pii(data[key])
    elif isinstance(data, list):
        data = [_sanitize_no_pii(item) if isinstance(item, (dict, list)) else item for item in data]
    return data


def export_vision_summary(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
) -> Path:
    """Export vision attribute summary."""
    # Attribute counts
    attr_counts = conn.execute(
        """
        SELECT attribute_code, count(*) as image_count,
               avg(confidence_score) as avg_confidence,
               sum(CASE WHEN is_accepted THEN 1 ELSE 0 END) as accepted_count
        FROM feature_image_attribute
        WHERE label_source != 'derived_rule'
        GROUP BY attribute_code
        ORDER BY image_count DESC
        """
    ).fetchall()

    # Confidence distribution
    conf_dist = conn.execute(
        """
        SELECT
            CASE
                WHEN confidence_score >= 0.80 THEN 'accepted'
                WHEN confidence_score >= 0.50 THEN 'tentative'
                ELSE 'rejected'
            END as classification,
            count(*) as count
        FROM feature_image_attribute
        WHERE label_source != 'derived_rule'
        GROUP BY classification
        """
    ).fetchall()

    data = {
        "attributes": [
            {
                "code": r[0],
                "image_count": r[1],
                "avg_confidence": round(r[2], 4) if r[2] else None,
                "accepted_count": r[3],
            }
            for r in attr_counts
        ],
        "confidence_distribution": [
            {"classification": r[0], "count": r[1]} for r in conf_dist
        ],
        "total_images_tagged": conn.execute(
            "SELECT count(DISTINCT image_sk) FROM feature_image_attribute"
        ).fetchone()[0],
    }

    path = output_dir / "vision-summary.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def export_voting_block_summary(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
    scenario_id: str,
) -> Path:
    """Export voting block summary for a scenario."""
    scenario = conn.execute(
        "SELECT scenario_name, description FROM dim_voting_scenario WHERE scenario_id = ?",
        [scenario_id],
    ).fetchone()

    blocks = conn.execute(
        """
        SELECT bs.block_id, db.block_label, bs.voter_count, bs.vote_count,
               bs.detection_status
        FROM mart_voting_block_summary bs
        JOIN dim_voting_block db ON bs.block_id = db.block_id AND bs.scenario_id = db.scenario_id
        WHERE bs.scenario_id = ?
        """,
        [scenario_id],
    ).fetchall()

    # Per-block top attribute lifts
    block_cards = []
    for block_id, label, voter_count, vote_count, detection in blocks:
        top_lift = conn.execute(
            """
            SELECT attribute_code, lift
            FROM mart_voting_block_attribute_lift
            WHERE scenario_id = ? AND block_id = ?
            ORDER BY lift DESC LIMIT 3
            """,
            [scenario_id, block_id],
        ).fetchall()

        # Rule summary
        rules = conn.execute(
            "SELECT rule_type, attribute_code FROM voting_block_rule WHERE scenario_id = ? AND block_id = ?",
            [scenario_id, block_id],
        ).fetchall()
        rule_summary = []
        for rtype, code in rules:
            rule_summary.append(f"{rtype}: {code}")

        block_cards.append({
            "block_id": block_id,
            "label": label,
            "voter_count": voter_count,
            "vote_count": vote_count,
            "rule_summary": rule_summary,
            "top_attribute_lifts": [
                {"attribute": r[0], "lift": round(r[1], 2)} for r in top_lift
            ],
            "detection_status": detection,
        })

    data = {
        "scenario_id": scenario_id,
        "scenario_name": scenario[0] if scenario else scenario_id,
        "description": scenario[1] if scenario else "",
        "block_count": len(blocks),
        "total_voters": sum(b["voter_count"] for b in block_cards),
        "total_votes": sum(b["vote_count"] for b in block_cards),
        "blocks": block_cards,
    }

    path = output_dir / "voting-block-summary.json"
    path.write_text(json.dumps(_sanitize_no_pii(data), indent=2), encoding="utf-8")
    return path


def export_attribute_lift(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
    scenario_id: str,
) -> Path:
    """Export attribute lift data."""
    rows = conn.execute(
        """
        SELECT block_id, attribute_code, block_selection_rate, global_selection_rate,
               lift, odds_ratio, selected_count, exposed_count,
               confidence_interval_low, confidence_interval_high
        FROM mart_voting_block_attribute_lift
        WHERE scenario_id = ?
        ORDER BY block_id, lift DESC
        """,
        [scenario_id],
    ).fetchall()

    data = [
        {
            "block_id": r[0], "attribute_code": r[1],
            "block_selection_rate": r[2], "global_selection_rate": r[3],
            "lift": r[4], "odds_ratio": r[5],
            "selected_count": r[6], "exposed_count": r[7],
            "ci_low": r[8], "ci_high": r[9],
        }
        for r in rows
    ]

    path = output_dir / "voting-block-attribute-lift.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def export_cluster_lift(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
    scenario_id: str,
) -> Path:
    """Export cluster lift data."""
    rows = conn.execute(
        """
        SELECT block_id, cluster_id, cluster_label, block_selection_rate,
               global_selection_rate, lift, chi_square_contribution,
               selected_count, expected_count
        FROM mart_voting_block_cluster_lift
        WHERE scenario_id = ?
        ORDER BY block_id, lift DESC
        """,
        [scenario_id],
    ).fetchall()

    data = [
        {
            "block_id": r[0], "cluster_id": r[1], "cluster_label": r[2],
            "block_selection_rate": r[3], "global_selection_rate": r[4],
            "lift": r[5], "chi_square_contribution": r[6],
            "selected_count": r[7], "expected_count": r[8],
        }
        for r in rows
    ]

    path = output_dir / "voting-block-cluster-lift.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def export_score_impact(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
    scenario_id: str,
) -> Path:
    """Export score impact (top promoted/suppressed images per block)."""
    rows = conn.execute(
        """
        SELECT block_id, image_sk, score_with_block, score_without_block,
               score_delta, rank_with_block, rank_without_block, rank_delta,
               block_influence_score
        FROM mart_voting_block_score_impact
        WHERE scenario_id = ?
        ORDER BY block_id, block_influence_score DESC
        """,
        [scenario_id],
    ).fetchall()

    data = [
        {
            "block_id": r[0], "image_sk": r[1],
            "score_with_block": r[2], "score_without_block": r[3],
            "score_delta": r[4], "rank_with_block": r[5],
            "rank_without_block": r[6], "rank_delta": r[7],
            "influence_score": r[8],
        }
        for r in rows
    ]

    path = output_dir / "voting-block-score-impact.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def export_calendar_impact(
    conn: duckdb.DuckDBPyConnection,
    output_dir: Path,
    scenario_id: str,
) -> Path:
    """Export calendar impact data."""
    row = conn.execute(
        """
        SELECT selected_images_with_json, selected_images_without_json,
               cover_image_with, cover_image_without,
               changed_month_count, changed_cover_flag
        FROM mart_voting_block_calendar_impact
        WHERE scenario_id = ?
        """,
        [scenario_id],
    ).fetchone()

    if row:
        data = {
            "scenario_id": scenario_id,
            "selected_images_with_blocks": json.loads(row[0]) if row[0] else [],
            "selected_images_without_blocks": json.loads(row[1]) if row[1] else [],
            "cover_image_with_blocks": row[2],
            "cover_image_without_blocks": row[3],
            "changed_month_count": row[4],
            "changed_cover": row[5],
        }
    else:
        data = {"scenario_id": scenario_id, "error": "No calendar impact data found"}

    path = output_dir / "voting-block-calendar-impact.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def export_all_static_json(
    conn: duckdb.DuckDBPyConnection,
    scenario_id: str,
    output_dir: Path | None = None,
) -> dict[str, str]:
    """Export all static JSON files for the public site. Returns paths."""
    odir = output_dir or DEFAULT_OUTPUT_DIR
    odir.mkdir(parents=True, exist_ok=True)

    paths = {}

    # Vision summary (scenario-independent)
    try:
        paths["vision_summary"] = str(export_vision_summary(conn, odir))
    except Exception:
        logger.exception("Failed to export vision summary")

    # Scenario-specific exports
    paths["voting_block_summary"] = str(export_voting_block_summary(conn, odir, scenario_id))
    paths["attribute_lift"] = str(export_attribute_lift(conn, odir, scenario_id))
    paths["cluster_lift"] = str(export_cluster_lift(conn, odir, scenario_id))
    paths["score_impact"] = str(export_score_impact(conn, odir, scenario_id))
    paths["calendar_impact"] = str(export_calendar_impact(conn, odir, scenario_id))

    # Verify no PII leaked
    for name, path in paths.items():
        content = Path(path).read_text(encoding="utf-8")
        for field in ("voter_sk", "voter_public_hash", "random_seed"):
            if field in content:
                logger.warning(f"PII field {field!r} found in {name} export!")

    logger.info(f"Exported {len(paths)} static JSON files to {odir}")
    return paths
