# Session Startup — Phase 2A: Feature Extraction & Clustering

Use this file to reload context after a `/clear` or new session. Read these files in order.

## 1. Project Context

```
Read CLAUDE.md
Read docs/pdr.md (sections 17 and 22 — feature store tables and cluster analysis)
Read docs/pdr_revisions.md (sections 6–10 — clustering design, month/cover scoring)
```

## 2. Active Plan

```
Read docs/feature_extraction_plan.md
```

This is the active implementation plan. Check which phase/task is currently `Started` or the next `Open` row to know where work left off.

## 3. Current Schema

```
Read migrations/005_create_feature_tables.sql
```

If this file doesn't exist yet, Phase 1 hasn't started. If it does, check whether it has been applied:

```bash
artemis-pipeline status
```

## 4. Implementation Files

Read whichever of these exist — they are created progressively across phases:

```
Read src/artemis_calendar/features/visual.py
Read src/artemis_calendar/features/embeddings.py
Read src/artemis_calendar/features/text_features.py
Read src/artemis_calendar/cluster/clustering.py
Read src/artemis_calendar/cluster/marts.py
Read src/artemis_calendar/cli.py
```

## 5. Dependencies

```
Read pyproject.toml
```

Check whether the `[project.optional-dependencies] ml` group exists. If not, Phase 1 hasn't completed.

## 6. Test State

```bash
pytest --tb=short
ruff check src/ tests/
```

## 7. Data State

Check what's in the warehouse:

```bash
duckdb D:/artemis/warehouse.duckdb -c "
  SELECT 'dim_image' as tbl, COUNT(*) as rows FROM dim_image
  UNION ALL SELECT 'feature_image_visual', COUNT(*) FROM feature_image_visual
  UNION ALL SELECT 'feature_image_embedding', COUNT(*) FROM feature_image_embedding
  UNION ALL SELECT 'feature_description_embedding', COUNT(*) FROM feature_description_embedding
  UNION ALL SELECT 'feature_description_text', COUNT(*) FROM feature_description_text
  UNION ALL SELECT 'feature_image_cluster', COUNT(*) FROM feature_image_cluster
"
```

If tables don't exist, the migration hasn't run. If row counts are zero, that extraction step hasn't run yet.

## 8. Key Facts

- **Branch:** main
- **Warehouse:** `D:/artemis/warehouse.duckdb`
- **Images:** `D:/artemis/raw/images/thumbs/{guid}.jpg` (thumbnails), `D:/artemis/raw/images/large/{guid}.JPG` (full)
- **12,736 images** in `dim_image`, **8 categories** in `dim_category`
- **Synthetic votes exist:** 100 voters, batch/pairwise/category vote fact tables populated
- **Embedding models:** CLIP `openai/clip-vit-base-patch32` (512-dim), sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Embeddings stored as:** DuckDB `FLOAT[]` arrays
- **Multimodal clustering weights:** visual 0.60, text 0.30, metadata 0.10
- **Score columns in marts are NULL** until Phase 3 (statistical modeling) backfills them
- **ML deps are optional:** `pip install -e ".[ml]"`
