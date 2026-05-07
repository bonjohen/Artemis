# Artemis

Data science and data engineering platform for selecting a high-quality **Artemis II 13-month calendar image collection** (December 2026 through December 2027).

The core problem is **collection optimization, not top-N ranking** — selecting 13 images that work together as a calendar (1 cover + 12 monthly pages), balancing voter preference, visual diversity, mission coverage, month suitability, and redundancy control.

Imagery and voting data are sourced from [ArtemisTimeline.com](https://artemistimeline.com), which hosts ~12,000 Artemis II mission photos with three voting modes: random-batch, head-to-head Elo, and category top-3 ranking.

## Status

Early implementation. The data collection pipeline (metadata ingestion, image download, synthetic vote generation) is in place. Statistical modeling and calendar optimization are not yet implemented.

## Architecture

The project follows a layered warehouse pattern:

**Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports**

Package layout under `src/artemis_calendar/`:

| Module | Purpose |
|---|---|
| `config/` | Source manifests, settings, paths |
| `extract/` | Download source pages, manifests, images, vote data |
| `load/` | Staging and warehouse loaders |
| `parse/` | Source-specific parsers |
| `validate/` | Schema, grain, referential, drift, semantic checks |
| `observe/` | Run manifests, logs, metrics |
| `synthetic/` | Synthetic voter data generation for bias detection testing |
| `cli.py` | CLI entry point |

## Requirements

- Python 3.11+
- [DuckDB](https://duckdb.org/) (embedded analytical database)

## Setup

```bash
# Clone the repository
git clone https://github.com/bonjohen/Artemis.git
cd Artemis

# Install in development mode
pip install -e ".[dev]"
```

## Usage

```bash
# Run the data pipeline
artemis-pipeline --help
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

- [`calendar_design.md`](calendar_design.md) — Calendar product spec (13-month layout, page layout, cover selection)
- [`docs/pdr.md`](docs/pdr.md) — Physical Design Review (data model, pipeline architecture, statistical methods)
- [`docs/pdr_revisions.md`](docs/pdr_revisions.md) — PDR addenda (archive/refresh pipeline, clustering, month/cover scoring)
- [`docs/synthetic_vote_pdr.md`](docs/synthetic_vote_pdr.md) — Synthetic voter data generator design

## Privacy

- No raw voter IDs are stored; only salted hashes
- Public reports contain aggregate counts, image-level scores, and cluster summaries — never voter-level data

## License

Private repository. All rights reserved.
