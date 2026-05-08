"""Vision tagging pipeline: orchestrate tagging, store results, generate outputs."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from artemis_calendar.config.settings import OUTPUT_ROOT, RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status
from artemis_calendar.vision.attributes import AttributeVocabulary, load_attribute_vocabulary
from artemis_calendar.vision.loader import write_image_attributes

logger = get_logger("artemis.vision.pipeline")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"
VISION_OUTPUT_DIR = OUTPUT_ROOT / "vision"


def _should_flag_for_review(
    confidences: dict[str, float],
    vocab: AttributeVocabulary,
) -> tuple[bool, list[str]]:
    """Determine if an image should be flagged for manual review.

    Returns (flag, reasons).
    """
    reasons = []

    # Low overall confidence (few attributes above tentative)
    above_tentative = sum(
        1 for v in confidences.values()
        if v >= vocab.thresholds.tentative
    )
    if above_tentative < 2:
        reasons.append("low_overall_confidence")

    # Conflicting core attributes
    surface = confidences.get("surface", 0)
    deep_space = confidences.get("deep_space", 0)
    if surface >= vocab.thresholds.accepted and deep_space >= vocab.thresholds.accepted:
        reasons.append("conflicting_surface_and_deep_space")

    # Media types that are unusual for a photo collection
    for media_attr in ("diagram", "map", "text_overlay", "artistic_rendering"):
        if confidences.get(media_attr, 0) >= vocab.thresholds.tentative:
            reasons.append(f"unusual_media_type_{media_attr}")

    # Low confidence flag from model
    if confidences.get("low_confidence", 0) >= vocab.thresholds.tentative:
        reasons.append("model_reports_low_confidence")

    return len(reasons) > 0, reasons


def run_vision_tagging(
    conn: duckdb.DuckDBPyConnection,
    *,
    tagger,
    vocab: AttributeVocabulary | None = None,
    limit: int | None = None,
    changed_only: bool = False,
    output_dir: Path | None = None,
    thumb_dir: Path | None = None,
) -> dict:
    """Run the full vision tagging pipeline.

    Args:
        conn: Database connection.
        tagger: A VisionTagger or MockTagger instance.
        vocab: Attribute vocabulary (loaded from config if None).
        limit: Max images to process.
        changed_only: Skip images that already have attribute records.
        output_dir: Where to write outputs (default: OUTPUT_ROOT/vision/).
        thumb_dir: Thumbnail directory (default: RAW_ROOT/images/thumbs/).

    Returns:
        Summary dict with counts and output paths.
    """
    if vocab is None:
        vocab = load_attribute_vocabulary()

    tdir = thumb_dir or THUMB_DIR
    odir = output_dir or VISION_OUTPUT_DIR
    odir.mkdir(parents=True, exist_ok=True)

    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="vision-tag-images",
        dataset_name="feature_image_attribute",
        source_name="thumbnails",
    )

    # Get images to process
    query = """
        SELECT di.image_sk, di.source_image_id
        FROM dim_image di
        WHERE di.thumb_downloaded = true
    """
    if changed_only:
        query += """
          AND di.image_sk NOT IN (
              SELECT DISTINCT image_sk FROM feature_image_attribute
              WHERE run_id IS NOT NULL
          )
        """
    query += " ORDER BY di.image_sk"
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    logger.info(f"Found {len(rows)} images to tag")

    if not rows:
        update_run_status(conn, run_id, row_count_raw=0, row_count_loaded=0, load_status="complete")
        return {"run_id": run_id, "images_processed": 0, "attributes_written": 0}

    # Collect image paths
    image_infos = []
    for image_sk, source_image_id in rows:
        thumb_path = tdir / f"{source_image_id}.jpg"
        if not thumb_path.exists():
            thumb_path = tdir / f"{source_image_id}.JPG"
        if thumb_path.exists():
            image_infos.append((image_sk, source_image_id, thumb_path))
        else:
            logger.warning(f"Thumbnail not found for {source_image_id}")

    # Tag all images
    image_paths = [info[2] for info in image_infos]

    def _progress(done, total):
        if done % 100 == 0 or done == total:
            logger.info(f"Tagged {done}/{total} images")

    all_confidences = tagger.tag_batch(image_paths, progress_callback=_progress)

    # Write results to database and build output
    total_attrs = 0
    output_records = []
    review_flagged = 0

    for (image_sk, source_image_id, _), confidences in zip(image_infos, all_confidences, strict=True):
        count = write_image_attributes(
            conn,
            image_sk=image_sk,
            base_confidences=confidences,
            vocab=vocab,
            model_name=tagger.model_name,
            model_version=tagger.model_version,
            run_id=run_id,
        )
        total_attrs += count

        # Compute derived labels and review flag
        accepted_labels = vocab.compute_accepted_base_labels(confidences)
        derived_labels = vocab.compute_derived_labels(confidences)
        review_flag, review_reasons = _should_flag_for_review(confidences, vocab)
        if review_flag:
            review_flagged += 1

        output_records.append({
            "image_sk": image_sk,
            "source_image_id": source_image_id,
            "attributes": confidences,
            "accepted_labels": accepted_labels,
            "derived_labels": derived_labels,
            "vision_model": tagger.model_name,
            "model_version": tagger.model_version,
            "review_flag": review_flag,
            "review_reasons": review_reasons,
        })

    # Write output JSON
    output_path = odir / "image_attributes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2)

    update_run_status(
        conn, run_id,
        row_count_raw=len(image_infos),
        row_count_loaded=total_attrs,
        load_status="complete",
    )

    summary = {
        "run_id": run_id,
        "images_processed": len(image_infos),
        "attributes_written": total_attrs,
        "review_flagged": review_flagged,
        "output_path": str(output_path),
    }
    logger.info(f"Vision tagging complete: {summary}")
    return summary
