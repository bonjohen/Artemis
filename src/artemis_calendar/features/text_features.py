"""Text feature extraction from image descriptions: sentiment, topics, entities."""

from __future__ import annotations

import json
import re

import duckdb

from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status

logger = get_logger("artemis.features.text")

# Entity patterns for Artemis II mission
ENTITY_PATTERNS = {
    "Earth": re.compile(r"\bEarth\b", re.IGNORECASE),
    "Moon": re.compile(r"\bMoon\b", re.IGNORECASE),
    "Orion": re.compile(r"\bOrion\b", re.IGNORECASE),
    "SLS": re.compile(r"\bSLS\b|\bSpace Launch System\b", re.IGNORECASE),
    "crew": re.compile(
        r"\b(?:Reid Wiseman|Victor Glover|Christina Koch|Jeremy Hansen|crew|astronaut)\b",
        re.IGNORECASE,
    ),
    "spacecraft": re.compile(r"\bspacecraft\b|\bcapsule\b|\bmodule\b", re.IGNORECASE),
}


def _extract_entities(text: str) -> dict[str, bool]:
    """Find mission-relevant entities in text."""
    return {name: bool(pattern.search(text)) for name, pattern in ENTITY_PATTERNS.items()}


def _ensure_vader():
    """Download VADER lexicon if not already present."""
    import nltk

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)


def _extract_sentiment(text: str) -> tuple[float, float]:
    """Return (sentiment_score, subjectivity_score) using VADER.

    sentiment_score: compound score in [-1, 1]
    subjectivity_score: heuristic based on pos+neg proportion in [0, 1]
    """
    _ensure_vader()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(text)
    # Subjectivity heuristic: proportion of text that is not neutral
    subjectivity = scores["pos"] + scores["neg"]
    return scores["compound"], min(subjectivity, 1.0)


def _extract_topics(texts: list[str], top_n: int = 10) -> list[list[str]]:
    """Extract top TF-IDF terms per document."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not texts:
        return []

    vectorizer = TfidfVectorizer(max_features=500, stop_words="english", max_df=0.8, min_df=2)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Not enough documents or all stop words
        return [[] for _ in texts]

    feature_names = vectorizer.get_feature_names_out()
    topics = []
    for row_idx in range(tfidf_matrix.shape[0]):
        row = tfidf_matrix[row_idx].toarray().flatten()
        top_indices = row.argsort()[-top_n:][::-1]
        top_terms = [feature_names[i] for i in top_indices if row[i] > 0]
        topics.append(top_terms)
    return topics


def extract_text_features(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int | None = None,
    batch_size: int = 200,
) -> int:
    """Extract text features (sentiment, topics, entities) for images with descriptions.

    Returns the number of images processed.
    """
    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="extract_text_features",
        dataset_name="feature_description_text",
        source_name="dim_image",
    )

    query = """
        SELECT di.image_sk,
               COALESCE(di.title, '') || ' ' || COALESCE(di.description, '') AS combined_text
        FROM dim_image di
        WHERE (di.title IS NOT NULL OR di.description IS NOT NULL)
          AND di.image_sk NOT IN (SELECT image_sk FROM feature_description_text)
    """
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    logger.info(f"Found {len(rows)} images to extract text features for")

    if not rows:
        update_run_status(conn, run_id, row_count_raw=0, row_count_loaded=0, load_status="complete")
        return 0

    # Collect all texts for TF-IDF (needs the full corpus)
    all_image_sks = [r[0] for r in rows]
    all_texts = [r[1].strip() for r in rows]

    # Batch TF-IDF across all texts
    all_topics = _extract_topics(all_texts)

    processed = 0
    for i in range(0, len(rows), batch_size):
        batch_sks = all_image_sks[i : i + batch_size]
        batch_texts = all_texts[i : i + batch_size]
        batch_topics = all_topics[i : i + batch_size]

        for image_sk, text, topics in zip(batch_sks, batch_texts, batch_topics, strict=True):
            sentiment, subjectivity = _extract_sentiment(text)
            entities = _extract_entities(text)

            conn.execute(
                """
                INSERT INTO feature_description_text (
                    image_sk, feature_run_id, description_language,
                    sentiment_score, subjectivity_score,
                    topic_terms_json, entity_json
                ) VALUES (?, ?, 'en', ?, ?, ?, ?)
                """,
                [
                    image_sk,
                    run_id,
                    sentiment,
                    subjectivity,
                    json.dumps(topics),
                    json.dumps(entities),
                ],
            )
            processed += 1

        logger.info(f"Processed {min(i + batch_size, len(rows))}/{len(rows)} texts")

    update_run_status(conn, run_id, row_count_raw=len(rows), row_count_loaded=processed, load_status="complete")
    logger.info(f"Text feature extraction complete: {processed}/{len(rows)}")
    return processed
