"""Load attribute vocabulary into warehouse and write image attribute records."""

from __future__ import annotations

from pathlib import Path

import duckdb

from artemis_calendar.observe.logging import get_logger
from artemis_calendar.vision.attributes import (
    AttributeVocabulary,
    load_attribute_vocabulary,
)

logger = get_logger("artemis.vision.loader")


def seed_attribute_vocabulary(
    conn: duckdb.DuckDBPyConnection,
    config_path: Path | None = None,
) -> int:
    """Seed dim_image_attribute from the YAML config file.

    Upserts: updates existing rows and inserts new ones.
    Returns the total number of attributes loaded.
    """
    vocab = load_attribute_vocabulary(config_path)

    count = 0
    for attr in vocab.base_attributes:
        conn.execute(
            """
            INSERT INTO dim_image_attribute
                (attribute_code, attribute_label, attribute_description,
                 attribute_type, is_derived, updated_at)
            VALUES (?, ?, ?, ?, false, now())
            ON CONFLICT (attribute_code) DO UPDATE SET
                attribute_label = EXCLUDED.attribute_label,
                attribute_description = EXCLUDED.attribute_description,
                attribute_type = EXCLUDED.attribute_type,
                is_derived = false,
                updated_at = now()
            """,
            [attr.code, attr.label, attr.description, attr.type],
        )
        count += 1

    for attr in vocab.derived_attributes:
        conn.execute(
            """
            INSERT INTO dim_image_attribute
                (attribute_code, attribute_label, attribute_description,
                 attribute_type, is_derived, updated_at)
            VALUES (?, ?, ?, 'derived', true, now())
            ON CONFLICT (attribute_code) DO UPDATE SET
                attribute_label = EXCLUDED.attribute_label,
                attribute_description = EXCLUDED.attribute_description,
                attribute_type = 'derived',
                is_derived = true,
                updated_at = now()
            """,
            [attr.code, attr.label, attr.description],
        )
        count += 1

    logger.info(f"Seeded {count} attributes into dim_image_attribute")
    return count


def write_image_attributes(
    conn: duckdb.DuckDBPyConnection,
    *,
    image_sk: int,
    base_confidences: dict[str, float],
    vocab: AttributeVocabulary,
    model_name: str,
    model_version: str,
    run_id: str,
) -> int:
    """Write attribute confidence scores for a single image.

    Computes classification (accepted/tentative/rejected) and derived labels.
    Returns the number of attribute rows written.
    """
    count = 0

    # Write base attribute scores
    for code, confidence in base_confidences.items():
        if code not in vocab.base_codes:
            logger.warning(f"Skipping unknown attribute {code!r} for image_sk={image_sk}")
            continue

        classification = vocab.classify_confidence(confidence)
        is_accepted = classification == "accepted"

        conn.execute(
            """
            INSERT INTO feature_image_attribute
                (image_sk, attribute_code, confidence_score, classification,
                 label_source, model_name, model_version, run_id, is_accepted)
            VALUES (?, ?, ?, ?, 'vision_model', ?, ?, ?, ?)
            """,
            [image_sk, code, confidence, classification,
             model_name, model_version, run_id, is_accepted],
        )
        count += 1

    # Write derived attribute labels (confidence = 1.0 since they're rule-based)
    derived_labels = vocab.compute_derived_labels(base_confidences)
    for code in derived_labels:
        conn.execute(
            """
            INSERT INTO feature_image_attribute
                (image_sk, attribute_code, confidence_score, classification,
                 label_source, model_name, model_version, run_id, is_accepted)
            VALUES (?, ?, 1.0, 'accepted', 'derived_rule', ?, ?, ?, true)
            """,
            [image_sk, code, model_name, model_version, run_id],
        )
        count += 1

    return count
