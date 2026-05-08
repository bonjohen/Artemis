# Artemis

Data science and data engineering platform for selecting a high-quality **Artemis II 13-month calendar image collection** (December 2026 through December 2027).

The core problem is **collection optimization, not top-N ranking** — selecting 13 images that work together as a calendar (1 cover + 12 monthly pages), balancing voter preference, visual diversity, mission coverage, month suitability, and redundancy control.

Imagery and voting data are sourced from [ArtemisTimeline.com](https://artemistimeline.com), which hosts ~12,000 Artemis II mission photos with three voting modes: random-batch, head-to-head Elo, and category top-3 ranking.

## Status

**Through Phase S3-S4.** The full data pipeline, calendar optimization, rendering, review package, synthetic validation, and interactive web app are operational:

- **12,217 thumbnails** downloaded from Cloudflare R2 CDN (concurrent, ~2.7 min)
- **Visual features** extracted for all images (brightness, contrast, saturation, dominant colors)
- **CLIP embeddings** (512-dim) for all 12,217 vote-pool images
- **k-means clustering** (k=25) across visual, text, and multimodal views
- **Statistical modeling** — Beta-Binomial posteriors, Elo ratings, Borda scores, composite scoring, inter-rater reliability
- **Calendar optimization** — 5 selection methods, Hungarian month assignment, 5 candidate calendars generated
- **Calendar rendering** — targeted full-res download, 8.5x11 page layout, cover + 13 monthly pages, multi-page PDF assembly
- **Review package** — candidate comparison scorecard, contact sheets, selection reports, layout validation, export assembly
- **Synthetic validation** — bias detection (position, cluster, voter segments), calendar optimization validation
- **Web app** — FastAPI + vanilla JS SPA for interactive image browsing, candidate comparison, cluster exploration, stats dashboard, and custom calendar selection with live scoring

## Architecture

The project follows a layered warehouse pattern:

**Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports**

Package layout under `src/artemis_calendar/`:

| Module | Purpose |
|---|---|
| `config/` | Source manifests, settings, paths, database connection |
| `extract/` | Download source pages, manifests, images (concurrent downloader) |
| `parse/` | Source-specific parsers (timeline, category, leaderboard, vote manifest) |
| `load/` | Staging and warehouse loaders |
| `validate/` | Schema, grain, referential, drift, semantic checks |
| `observe/` | Run manifests, structured JSON logging |
| `features/` | Image/text embeddings, visual features (parallel extraction) |
| `cluster/` | Visual, text, multimodal clustering + mart builders |
| `synthetic/` | Synthetic voter data generation for bias detection testing |
| `models/` | Preference scoring (Elo, Borda, Beta-Binomial), composite scores, reliability |
| `optimize/` | Calendar slate generation, month/cover scoring, 5 selection methods, Hungarian assignment |
| `render/` | Calendar page rendering: layout, grid, monthly/cover pages, pipeline, PDF assembly |
| `review/` | Review package: comparison, contact sheet, selection report, validation, export |
| `web/` | FastAPI web app: API endpoints, SPA frontend, interactive selection builder |
| `cli.py` | CLI entry point |

## Requirements

- Python 3.11+
- [DuckDB](https://duckdb.org/) (embedded analytical database)

## Setup

```bash
# Clone the repository
git clone https://github.com/bonjohen/Artemis.git
cd Artemis

# Install in development mode (core dependencies)
pip install -e ".[dev]"

# Install ML dependencies (CLIP, sentence-transformers, sklearn, etc.)
pip install -e ".[ml]"

# Install web app dependencies (FastAPI + uvicorn)
pip install -e ".[web]"
```

## Usage

```bash
# Show available commands
artemis-pipeline --help

# Run the full pipeline (metadata → load → synthetic votes → features → clustering)
artemis-pipeline run-all

# Or run individual steps:
artemis-pipeline migrate                  # Apply database migrations
artemis-pipeline status                   # Show warehouse table counts
artemis-pipeline collect-metadata         # Download metadata from sources
artemis-pipeline load-metadata            # Parse and load into warehouse
artemis-pipeline collect-images --thumbs-only  # Download thumbnails
artemis-pipeline generate-votes           # Generate synthetic vote data
artemis-pipeline extract-visual           # Extract Pillow-based visual features
artemis-pipeline extract-embeddings       # Generate CLIP + text embeddings
artemis-pipeline run-clustering --algorithm kmeans --cluster-type all --n-clusters 25 --seed 42
artemis-pipeline compute-scores            # Compute preference scores (Elo, Borda, composite)
artemis-pipeline optimize                  # Generate 5 candidate calendars
artemis-pipeline optimize --methods method_a,method_e  # Run specific methods only
artemis-pipeline render-calendar --candidate method_b  # Render calendar PDF for best candidate
artemis-pipeline render-calendar --all                 # Render all 5 candidates
artemis-pipeline serve                                 # Start web app on localhost:8420
artemis-pipeline serve --port 9000                     # Custom port
```

## Viewing Clustering Results

After clustering completes, you can explore the results directly in DuckDB. Start a Python session or use the DuckDB CLI:

```python
from artemis_calendar.config.database import get_connection, apply_migrations
conn = get_connection()
apply_migrations(conn)
```

### Cluster summary — how many images per cluster, which image is most representative

```sql
SELECT cluster_type, cluster_id, image_count, top_image_sk
FROM mart_image_cluster_summary
WHERE cluster_run_id = (
    SELECT DISTINCT cluster_run_id FROM feature_image_cluster LIMIT 1
)
ORDER BY cluster_type, image_count DESC;
```

### Top images per cluster — the 5 images closest to each cluster centroid

```sql
SELECT ct.cluster_type, ct.cluster_id, ct.rank_in_cluster, ct.image_sk,
       di.source_image_id
FROM mart_cluster_top_images ct
JOIN dim_image di ON di.image_sk = ct.image_sk
WHERE ct.cluster_run_id = (
    SELECT DISTINCT cluster_run_id FROM feature_image_cluster LIMIT 1
)
ORDER BY ct.cluster_type, ct.cluster_id, ct.rank_in_cluster;
```

### Cluster size distribution — see how balanced the clusters are

```sql
SELECT cluster_type, cluster_id, count(*) AS n
FROM feature_image_cluster
GROUP BY cluster_type, cluster_id
ORDER BY cluster_type, n DESC;
```

### Find which cluster an image belongs to

```sql
SELECT fic.cluster_type, fic.cluster_id, fic.distance_to_centroid,
       di.source_image_id
FROM feature_image_cluster fic
JOIN dim_image di ON di.image_sk = fic.image_sk
WHERE di.source_image_id = 'ART002-E-29996';
```

### Visual features for an image

```sql
SELECT di.source_image_id, fv.orientation, fv.aspect_ratio,
       fv.brightness_score, fv.contrast_score, fv.saturation_score,
       fv.dominant_color_json
FROM feature_image_visual fv
JOIN dim_image di ON di.image_sk = fv.image_sk
WHERE di.source_image_id = 'ART002-E-29996';
```

### View a thumbnail

Thumbnails are stored at `D:/artemis/raw/images/thumbs/{source_image_id}.jpg`. Open any image to see what a cluster's representative images look like:

```python
from PIL import Image
img = Image.open("D:/artemis/raw/images/thumbs/ART002-E-29996.jpg")
img.show()
```

## Development

```bash
# Run tests
pytest

# Lint and format
ruff check src/ tests/
ruff format --check src/ tests/
```

## Documentation

Design documents live in `docs/`:

- [`docs/calendar_design.md`](docs/calendar_design.md) — Calendar product spec (13-month layout, page layout, cover selection)
- [`docs/pdr.md`](docs/pdr.md) — Physical Design Review (data model, pipeline architecture, statistical methods)
- [`docs/pdr_revisions.md`](docs/pdr_revisions.md) — PDR addenda (archive/refresh pipeline, clustering, month/cover scoring)
- [`docs/synthetic_vote_pdr.md`](docs/synthetic_vote_pdr.md) — Synthetic voter data generator design
- [`docs/thumbnail_download_plan.md`](docs/thumbnail_download_plan.md) — Thumbnail download and full-scale extraction plan
- [`docs/statistical_modeling_design.md`](docs/statistical_modeling_design.md) — Phase 3 scoring design
- [`docs/calendar_optimization_design.md`](docs/calendar_optimization_design.md) — Phase 4 optimization design
- [`docs/calendar_rendering_plan.md`](docs/calendar_rendering_plan.md) — Phase C4 rendering plan

Lessons learned: [`docs/lessons/`](docs/lessons/) — 35 lessons across 5 blocks (infrastructure, statistical methods, optimization, validation, web app). View as a browsable web page: serve `docs/lessons/` and open [`lessons.html`](docs/lessons/lessons.html).

Session startup guide: [`startup.md`](startup.md) (root directory)

## Privacy

- No raw voter IDs are stored; only salted hashes
- Public reports contain aggregate counts, image-level scores, and cluster summaries — never voter-level data

## License

Private repository. All rights reserved.
