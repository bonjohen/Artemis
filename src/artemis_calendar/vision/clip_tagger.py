"""CLIP zero-shot image classification for content tagging.

Uses HuggingFace CLIP (openai/clip-vit-base-patch32) on CPU to classify
12K+ thumbnails against the attribute vocabulary. No GPU required.
"""

from __future__ import annotations

import time
from pathlib import Path

import duckdb
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from artemis_calendar.config.settings import DB_PATH, RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.vision.attributes import (
    AttributeVocabulary,
    load_attribute_vocabulary,
)

logger = get_logger("artemis.vision.clip_tagger")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"

# CLIP prompt engineering: wrap attribute descriptions in a photo context
# to get better zero-shot performance than bare labels.
PROMPT_TEMPLATE = "a photo of {description}"


def _build_label_prompts(vocab: AttributeVocabulary) -> list[tuple[str, str]]:
    """Build (code, prompt) pairs from the vocabulary."""
    pairs = []
    for attr in vocab.base_attributes:
        prompt = PROMPT_TEMPLATE.format(description=attr.description.lower())
        pairs.append((attr.code, prompt))
    return pairs


def _load_clip():
    """Load CLIP model and processor."""
    logger.info("Loading CLIP model (openai/clip-vit-base-patch32)...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    logger.info("CLIP model loaded.")
    return model, processor


def _classify_batch(
    model: CLIPModel,
    processor: CLIPProcessor,
    image_paths: list[Path],
    prompts: list[str],
) -> list[list[float]]:
    """Classify a batch of images against all prompts.

    Uses CLIP cosine similarity converted to a [0,1] score via sigmoid
    scaling. Each attribute gets an independent score based on how strongly
    the image-text similarity exceeds a baseline threshold.

    Returns list of score lists, one per image. Each score list has
    len(prompts) independent scores.
    """
    images = []
    for p in image_paths:
        try:
            img = Image.open(p).convert("RGB")
            images.append(img)
        except Exception:
            images.append(Image.new("RGB", (150, 100)))

    inputs = processor(
        text=prompts,
        images=images,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        # logits_per_image: (batch, num_prompts) — scaled cosine similarity
        logits = outputs.logits_per_image

        # Convert logits to independent [0,1] scores per attribute.
        # CLIP logits are cosine_similarity * temperature (default ~100).
        # Logit distribution for Artemis photos: mean ~24, range 16-32.
        # Sigmoid centered at 25.5 with scale 1.5 gives clean separation:
        # >27 → accepted (>0.84), 24-27 → tentative, <24 → rejected.
        scores = torch.sigmoid((logits - 25.5) / 1.5)

    return scores.tolist()


def tag_all_images(
    conn: duckdb.DuckDBPyConnection | None = None,
    vocab: AttributeVocabulary | None = None,
    batch_size: int = 32,
    progress_callback=None,
) -> dict:
    """Tag all vote-pool thumbnails with CLIP zero-shot classification.

    Args:
        conn: DuckDB connection. Opens warehouse if None.
        vocab: Attribute vocabulary. Loads default if None.
        batch_size: Images per CLIP batch.
        progress_callback: Called with (done, total, elapsed_sec, rate) after each batch.

    Returns summary dict.
    """
    own_conn = conn is None
    if own_conn:
        conn = duckdb.connect(str(DB_PATH))

    if vocab is None:
        vocab = load_attribute_vocabulary()

    label_pairs = _build_label_prompts(vocab)
    codes = [c for c, _ in label_pairs]
    prompts = [p for _, p in label_pairs]

    # Get all vote-pool images
    rows = conn.execute(
        "SELECT image_sk, source_image_id FROM dim_image WHERE vote_pool_flag = true ORDER BY image_sk"
    ).fetchall()

    total = len(rows)
    logger.info(f"Tagging {total} images against {len(codes)} attributes...")

    model, processor = _load_clip()

    # Pre-encode text prompts once (they don't change per batch)
    # But CLIPProcessor handles this internally, so we pass prompts each time.

    # Clear existing CLIP-sourced attributes
    conn.execute("DELETE FROM feature_image_attribute WHERE label_source = 'clip_zero_shot'")

    start_time = time.time()
    done = 0
    tagged = 0
    skipped = 0
    insert_buffer = []

    for batch_start in range(0, total, batch_size):
        batch_rows = rows[batch_start : batch_start + batch_size]

        # Load images
        image_paths = []
        image_sks = []
        for image_sk, guid in batch_rows:
            path = THUMB_DIR / f"{guid}.jpg"
            if path.exists():
                image_paths.append(path)
                image_sks.append(int(image_sk))
            else:
                skipped += 1

        if not image_paths:
            done += len(batch_rows)
            continue

        # Classify
        batch_probs = _classify_batch(model, processor, image_paths, prompts)

        # Process results
        for i, image_sk in enumerate(image_sks):
            probs = batch_probs[i]

            # Compute derived labels from base confidences
            base_conf = {code: prob for code, prob in zip(codes, probs)}

            for code, prob in zip(codes, probs):
                classification = vocab.classify_confidence(prob)
                is_accepted = classification == "accepted"
                insert_buffer.append((
                    image_sk, code, round(prob, 4),
                    classification, "clip_zero_shot",
                    "clip-vit-base-patch32", "openai/clip-vit-base-patch32",
                    is_accepted,
                ))
                tagged += 1

            # Derived labels
            derived = vocab.compute_derived_labels(base_conf)
            for dcode in derived:
                insert_buffer.append((
                    image_sk, dcode, 1.0,
                    "accepted", "derived_rule",
                    None, None,
                    True,
                ))
                tagged += 1

        # Flush buffer periodically
        if len(insert_buffer) >= 5000:
            _flush_buffer(conn, insert_buffer)
            insert_buffer = []

        done += len(batch_rows)
        elapsed = time.time() - start_time
        rate = done / max(elapsed, 0.01)

        if progress_callback:
            progress_callback(done, total, elapsed, rate)

    # Final flush
    if insert_buffer:
        _flush_buffer(conn, insert_buffer)

    elapsed = time.time() - start_time

    summary = {
        "total_images": total,
        "tagged": done - skipped,
        "skipped": skipped,
        "attributes_written": tagged,
        "elapsed_seconds": round(elapsed, 1),
        "rate_images_per_sec": round((done - skipped) / max(elapsed, 0.01), 1),
    }

    logger.info(
        f"Tagging complete: {summary['tagged']} images, "
        f"{summary['attributes_written']} attribute rows, "
        f"{summary['elapsed_seconds']}s ({summary['rate_images_per_sec']} img/s)"
    )

    if own_conn:
        conn.close()

    return summary


def _flush_buffer(conn: duckdb.DuckDBPyConnection, buffer: list[tuple]) -> None:
    """Bulk insert attribute rows."""
    import pyarrow as pa

    if not buffer:
        return

    schema = pa.schema([
        ("image_sk", pa.int64()),
        ("attribute_code", pa.string()),
        ("confidence_score", pa.float64()),
        ("classification", pa.string()),
        ("label_source", pa.string()),
        ("model_name", pa.string()),
        ("model_version", pa.string()),
        ("is_accepted", pa.bool_()),
    ])

    arrays = [
        pa.array([r[0] for r in buffer], type=pa.int64()),
        pa.array([r[1] for r in buffer], type=pa.string()),
        pa.array([r[2] for r in buffer], type=pa.float64()),
        pa.array([r[3] for r in buffer], type=pa.string()),
        pa.array([r[4] for r in buffer], type=pa.string()),
        pa.array([r[5] for r in buffer], type=pa.string()),
        pa.array([r[6] for r in buffer], type=pa.string()),
        pa.array([r[7] for r in buffer], type=pa.bool_()),
    ]

    tbl = pa.table(arrays, schema=schema)
    conn.register("_attr_batch", tbl)
    conn.execute("""
        INSERT INTO feature_image_attribute
            (image_sk, attribute_code, confidence_score,
             classification, label_source, model_name, model_version,
             is_accepted)
        SELECT * FROM _attr_batch
    """)
    conn.unregister("_attr_batch")


def tag_new_attributes(
    conn: duckdb.DuckDBPyConnection | None = None,
    vocab: AttributeVocabulary | None = None,
    attribute_codes: list[str] | None = None,
    batch_size: int = 64,
    progress_callback=None,
) -> dict:
    """Tag images for specific attributes only (incremental).

    If attribute_codes is None, auto-detects codes present in the vocabulary
    but missing from feature_image_attribute.

    Only deletes and re-writes rows for the specified codes.
    """
    own_conn = conn is None
    if own_conn:
        conn = duckdb.connect(str(DB_PATH))

    if vocab is None:
        vocab = load_attribute_vocabulary()

    # Auto-detect missing codes
    if attribute_codes is None:
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT attribute_code FROM feature_image_attribute "
                "WHERE label_source = 'clip_zero_shot'"
            ).fetchall()
        }
        attribute_codes = [
            a.code for a in vocab.base_attributes if a.code not in existing
        ]
        if not attribute_codes:
            logger.info("No new attributes to tag — all vocabulary codes already exist.")
            if own_conn:
                conn.close()
            return {"new_codes": [], "attributes_written": 0}

    logger.info(f"Incremental tagging: {len(attribute_codes)} new codes: {attribute_codes}")

    # Build prompts for only the requested codes
    subset_pairs = [
        (a.code, PROMPT_TEMPLATE.format(description=a.description.lower()))
        for a in vocab.base_attributes
        if a.code in set(attribute_codes)
    ]
    if not subset_pairs:
        logger.warning(f"No matching base attributes for codes: {attribute_codes}")
        if own_conn:
            conn.close()
        return {"new_codes": attribute_codes, "attributes_written": 0}

    codes = [c for c, _ in subset_pairs]
    prompts = [p for _, p in subset_pairs]

    # Delete existing rows for these codes only
    for code in codes:
        conn.execute(
            "DELETE FROM feature_image_attribute "
            "WHERE attribute_code = ? AND label_source IN ('clip_zero_shot', 'derived_rule')",
            [code],
        )

    # Also delete derived attributes that depend on the new codes
    derived_to_recompute = []
    for da in vocab.derived_attributes:
        deps = set(da.rule.all_of) | set(da.rule.none_of)
        if deps & set(codes):
            derived_to_recompute.append(da.code)
            conn.execute(
                "DELETE FROM feature_image_attribute "
                "WHERE attribute_code = ? AND label_source = 'derived_rule'",
                [da.code],
            )

    # Get all vote-pool images
    rows = conn.execute(
        "SELECT image_sk, source_image_id FROM dim_image "
        "WHERE vote_pool_flag = true ORDER BY image_sk"
    ).fetchall()
    total = len(rows)

    model, processor = _load_clip()

    start_time = time.time()
    done = 0
    tagged = 0
    insert_buffer = []

    for batch_start in range(0, total, batch_size):
        batch_rows = rows[batch_start : batch_start + batch_size]

        image_paths = []
        image_sks = []
        for image_sk, guid in batch_rows:
            path = THUMB_DIR / f"{guid}.jpg"
            if path.exists():
                image_paths.append(path)
                image_sks.append(int(image_sk))

        if not image_paths:
            done += len(batch_rows)
            continue

        batch_probs = _classify_batch(model, processor, image_paths, prompts)

        for i, image_sk in enumerate(image_sks):
            probs = batch_probs[i]
            new_conf = {code: prob for code, prob in zip(codes, probs)}

            for code, prob in zip(codes, probs):
                classification = vocab.classify_confidence(prob)
                is_accepted = classification == "accepted"
                insert_buffer.append((
                    image_sk, code, round(prob, 4),
                    classification, "clip_zero_shot",
                    "clip-vit-base-patch32", "openai/clip-vit-base-patch32",
                    is_accepted,
                ))
                tagged += 1

            # Recompute affected derived attributes
            if derived_to_recompute:
                # Need full base confidences for derived rules
                existing_conf = dict(
                    conn.execute(
                        "SELECT attribute_code, confidence_score "
                        "FROM feature_image_attribute "
                        "WHERE image_sk = ? AND label_source = 'clip_zero_shot'",
                        [image_sk],
                    ).fetchall()
                )
                existing_conf.update(new_conf)
                derived = vocab.compute_derived_labels(existing_conf)
                for dcode in derived:
                    if dcode in derived_to_recompute:
                        insert_buffer.append((
                            image_sk, dcode, 1.0,
                            "accepted", "derived_rule",
                            None, None,
                            True,
                        ))
                        tagged += 1

        if len(insert_buffer) >= 5000:
            _flush_buffer(conn, insert_buffer)
            insert_buffer = []

        done += len(batch_rows)
        elapsed = time.time() - start_time
        rate = done / max(elapsed, 0.01)

        if progress_callback:
            progress_callback(done, total, elapsed, rate)

    if insert_buffer:
        _flush_buffer(conn, insert_buffer)

    elapsed = time.time() - start_time
    summary = {
        "new_codes": codes,
        "derived_recomputed": derived_to_recompute,
        "total_images": total,
        "attributes_written": tagged,
        "elapsed_seconds": round(elapsed, 1),
        "rate_images_per_sec": round(total / max(elapsed, 0.01), 1),
    }

    logger.info(
        f"Incremental tagging complete: {len(codes)} codes, "
        f"{tagged} rows, {summary['elapsed_seconds']}s"
    )

    if own_conn:
        conn.close()

    return summary
