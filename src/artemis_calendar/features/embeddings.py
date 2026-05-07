"""Image and text embedding generation using CLIP and sentence-transformers."""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
from PIL import Image

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.features.embeddings")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"

CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_DIMENSION = 512

TEXT_MODEL = "all-MiniLM-L6-v2"
TEXT_DIMENSION = 384


def _load_clip_model():
    """Load CLIP model and processor. Returns (model, processor)."""
    from transformers import CLIPModel, CLIPProcessor

    processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
    model = CLIPModel.from_pretrained(CLIP_MODEL)
    model.eval()
    return model, processor


def _load_text_model():
    """Load sentence-transformer model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(TEXT_MODEL)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_image_embeddings(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int | None = None,
    batch_size: int = 32,
    thumb_dir: Path | None = None,
) -> int:
    """Generate CLIP image embeddings for thumbnails not yet embedded.

    Returns the number of images processed.
    """
    import torch

    tdir = thumb_dir or THUMB_DIR
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="extract_image_embeddings",
        dataset_name="feature_image_embedding",
        source_name="thumbnails",
    )

    # Get images with thumbs that haven't been embedded with this model version
    query = """
        SELECT di.image_sk, di.source_image_id
        FROM dim_image di
        WHERE di.thumb_downloaded = true
          AND di.image_sk NOT IN (
              SELECT image_sk FROM feature_image_embedding
              WHERE embedding_model_version = ?
          )
    """
    params = [CLIP_MODEL]
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query, params).fetchall()
    logger.info(f"Found {len(rows)} images to generate CLIP embeddings for")

    if not rows:
        update_run_status(conn, run_id, row_count_raw=0, row_count_loaded=0, load_status="complete")
        return 0

    model, processor = _load_clip_model()
    processed = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        images = []
        valid_rows = []

        for image_sk, source_image_id in batch:
            thumb_path = tdir / f"{source_image_id}.jpg"
            if not thumb_path.exists():
                thumb_path = tdir / f"{source_image_id}.JPG"
            if not thumb_path.exists():
                continue

            try:
                img = Image.open(thumb_path).convert("RGB")
                image_bytes = thumb_path.read_bytes()
                images.append(img)
                valid_rows.append((image_sk, _sha256_bytes(image_bytes)))
            except Exception:
                logger.exception(f"Failed to load {source_image_id}")

        if not images:
            continue

        with torch.no_grad():
            inputs = processor(images=images, return_tensors="pt", padding=True)
            outputs = model.get_image_features(**inputs)
            # get_image_features returns BaseModelOutputWithPooling in newer transformers
            vectors = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
            # L2 normalize
            embeddings = vectors / vectors.norm(dim=-1, keepdim=True)
            embeddings = embeddings.cpu().numpy()

        for (image_sk, image_hash), embedding in zip(valid_rows, embeddings, strict=True):
            conn.execute(
                """
                INSERT INTO feature_image_embedding (
                    image_sk, embedding_model, embedding_model_version,
                    embedding_vector, embedding_dimension, source_image_hash
                ) VALUES (?, 'CLIP', ?, ?::FLOAT[], ?, ?)
                """,
                [image_sk, CLIP_MODEL, embedding.tolist(), CLIP_DIMENSION, image_hash],
            )
            processed += 1

        logger.info(f"Embedded {min(i + batch_size, len(rows))}/{len(rows)} images")

    update_run_status(conn, run_id, row_count_raw=len(rows), row_count_loaded=processed, load_status="complete")
    logger.info(f"Image embedding complete: {processed}/{len(rows)}")
    return processed


def extract_text_embeddings(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int | None = None,
    batch_size: int = 64,
) -> int:
    """Generate sentence-transformer text embeddings from image title + description.

    Returns the number of images processed.
    """
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="extract_text_embeddings",
        dataset_name="feature_description_embedding",
        source_name="dim_image",
    )

    query = """
        SELECT di.image_sk, COALESCE(di.title, '') || ' ' || COALESCE(di.description, '') AS combined_text
        FROM dim_image di
        WHERE (di.title IS NOT NULL OR di.description IS NOT NULL)
          AND di.image_sk NOT IN (
              SELECT image_sk FROM feature_description_embedding
              WHERE embedding_model_version = ?
          )
    """
    params = [TEXT_MODEL]
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query, params).fetchall()
    logger.info(f"Found {len(rows)} images to generate text embeddings for")

    if not rows:
        update_run_status(conn, run_id, row_count_raw=0, row_count_loaded=0, load_status="complete")
        return 0

    model = _load_text_model()
    processed = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        image_sks = [r[0] for r in batch]
        texts = [r[1].strip() for r in batch]
        text_hashes = [_sha256_text(t) for t in texts]

        embeddings = model.encode(texts, show_progress_bar=False)

        for image_sk, text_hash, embedding in zip(image_sks, text_hashes, embeddings, strict=True):
            conn.execute(
                """
                INSERT INTO feature_description_embedding (
                    image_sk, embedding_model, embedding_model_version,
                    text_source, embedding_vector, embedding_dimension, source_text_hash
                ) VALUES (?, 'sentence-transformers', ?, 'metadata_combined', ?::FLOAT[], ?, ?)
                """,
                [image_sk, TEXT_MODEL, embedding.tolist(), TEXT_DIMENSION, text_hash],
            )
            processed += 1

        logger.info(f"Embedded {min(i + batch_size, len(rows))}/{len(rows)} texts")

    update_run_status(conn, run_id, row_count_raw=len(rows), row_count_loaded=processed, load_status="complete")
    logger.info(f"Text embedding complete: {processed}/{len(rows)}")
    return processed
