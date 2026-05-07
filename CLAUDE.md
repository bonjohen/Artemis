# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Artemis is a data science and data engineering platform for selecting a high-quality **Artemis II 13-month calendar image collection** (December 2026 through December 2027). The core problem is **collection optimization, not top-N ranking** — selecting 13 images that work together as a calendar (1 cover + 12 monthly pages), balancing voter preference, visual diversity, mission coverage, month suitability, and redundancy control.

The project sources imagery and voting data from ArtemisTimeline.com, which hosts ~12,000 Artemis II mission photos with three voting modes: random-batch (50 shown, pick 5), head-to-head Elo, and category top-3 ranking.

## Project Status

**Pre-implementation / Design phase.** No code exists yet. The repository contains design documents only:

- `calendar_design.md` — Calendar product spec: 13-month layout, image selection methods, page layout (8.5x11 portrait), cover selection rules
- `docs/pdr.md` — Physical Design Review: full data model, pipeline architecture, warehouse schema, statistical methods, acceptance criteria
- `docs/pdr_revisions.md` — Addenda: archive/refresh pipeline, clustering design, month/cover scoring, lessons-learned registry, Pipeline Explorer
- `docs/synthetic_vote_pdr.md` — Synthetic voter data generator design for bias detection testing

## Architecture

The project follows a **JobClass-style layered warehouse pattern** (modeled after `github.com/bonjohen/jobclass`):

**Raw → Staging → Core → Feature Store → Modeling → Optimization → Marts → Reports**

Planned package layout under `src/artemis_calendar/`:

| Module | Purpose |
|---|---|
| `config/` | Source manifests, settings, paths |
| `extract/` | Download source pages, manifests, images, vote data |
| `archive/` | Immutable raw snapshot storage |
| `parse/` | Source-specific parsers |
| `load/` | Staging and warehouse loaders |
| `validate/` | Schema, grain, referential, drift, semantic checks |
| `observe/` | Run manifests, logs, metrics |
| `features/` | Image/text embeddings, sentiment, visual features |
| `models/` | Preference scoring (Elo, BTL, Bayesian), reliability models |
| `cluster/` | Visual, text, and multimodal clustering |
| `optimize/` | Calendar slate generation and month assignment |
| `marts/` | Analytical outputs |
| `reports/` | Review packages |

## Key Design Decisions

- **Immutable raw archive**: Every source snapshot preserved with content hash, never modified after capture
- **Natural grain preservation**: Vote events stored at their native grain (batch ballots, pairwise comparisons, category rankings) — not collapsed into single scores prematurely
- **Surrogate voter keys**: Anonymous voter continuity via `voter_sk` + hashed source IDs; no PII storage
- **Dual operating modes**: Full raw-vote mode (if data is provided) and aggregate-only fallback mode
- **Calendar as portfolio optimization**: Multi-objective function balancing preference, diversity, month fit, cover fit, mission coverage, minus redundancy/uncertainty penalties
- **13-image calendar**: Cover image must be one of the 13 monthly images, selected by composite popularity + cover suitability score

## Data Model Conventions

| Prefix | Object Type |
|---|---|
| `raw_` | Raw source tables |
| `stg_` | Staging tables |
| `dim_` | Dimension tables |
| `fact_` | Fact tables |
| `xref_` | Cross-reference tables |
| `bridge_` | Bridge tables |
| `feature_` | Feature store tables |
| `mart_` | Analytical mart tables |
| `ctl_` | Run control tables |
| `reject_` | Quarantine tables |

## Implementation Phases

The project uses a phased approach. Major phases:

- **Phase 0**: PDR closure and decisions (12 vs 13 images, aggregate-only prototype)
- **Phase 1**: Public data prototype (source snapshots, metadata ingestion)
- **Phase 1A**: JobClass pattern adaptation (extract → archive → parse → load → validate → observe pipeline skeleton)
- **Phase 2**: Raw vote ingestion (voter surrogates, batch/pairwise/category fact tables)
- **Phase 2A**: Clustering foundation (image/text/multimodal embeddings and clusters)
- **Phase 3**: Statistical modeling (exposure-adjusted scores, BTL, Elo, inter-rater reliability)
- **Phase 4**: Calendar optimization (objective function, month/cover scoring, candidate generation)
- **Phase 5**: Learning and publication package

Calendar-specific phases (C1–C5) cover selection methods, month assignment, cover selection, page rendering (8.5x11 PDF/PNG), and review packages.

Synthetic data phases (S1–S4) cover voter profile design, vote generation, bias detection validation, and calendar optimization validation.

## Documentation Structure

Design documents live in `docs/`. Once code exists, architecture and methodology docs should follow the numbered scheme from the PDR: `docs/00_project_overview.md` through `docs/15_methodology_for_publication.md`. Lessons learned go in `docs/lessons/` with structured entries (problem, why it matters, design choice, alternatives, what was learned).

## Privacy Constraints

- Never store raw voter IDs; use salted hashes
- Never attempt to identify voters
- Public reports: aggregate counts, image-level scores, cluster summaries, methodology — never voter-level rows
- Voter surrogates use identity confidence levels: exact, probable, weak, unknown
