"""Base configuration: environment handling, paths, constants."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

DATA_ROOT = Path(os.environ.get("ARTEMIS_DATA_ROOT", "D:/artemis"))
DB_PATH = Path(os.environ.get("ARTEMIS_DB_PATH", str(DATA_ROOT / "warehouse.duckdb")))
RAW_ROOT = Path(os.environ.get("ARTEMIS_RAW_ROOT", str(DATA_ROOT / "raw")))
LOG_DIR = Path(os.environ.get("ARTEMIS_LOG_DIR", str(DATA_ROOT / "logs")))
MANIFEST_PATH = Path(os.environ.get("ARTEMIS_MANIFEST_PATH", str(PROJECT_ROOT / "config" / "source_manifest.yaml")))
MIGRATIONS_DIR = Path(os.environ.get("ARTEMIS_MIGRATIONS_DIR", str(PROJECT_ROOT / "migrations")))

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CHECKSUM_ALGORITHM = "sha256"

OUTPUT_ROOT = Path(os.environ.get("ARTEMIS_OUTPUT_ROOT", str(DATA_ROOT / "output")))

DOWNLOAD_MAX_RETRIES = 3
DOWNLOAD_BACKOFF_SECONDS = 2.0

# Rate limiting for image downloads (seconds between requests)
RATE_LIMIT_NASA = 1.0
RATE_LIMIT_R2_CDN = 0.0
THUMB_DOWNLOAD_WORKERS = 3

# --- Calendar objective function weights ---
# Used by optimize/scoring.py to combine component scores into a single objective.
# These score a *complete* calendar slate (all 13 images together).
OBJECTIVE_W_POPULARITY = 2.0
OBJECTIVE_W_DIVERSITY = 1.5
OBJECTIVE_W_MONTH_FIT = 0.8
OBJECTIVE_W_COVER_FIT = 0.5
OBJECTIVE_W_REDUNDANCY = 1.0
OBJECTIVE_W_UNCERTAINTY = 0.3

# --- MMR greedy selection weights ---
# Used by optimize/methods.py method_e to score *individual candidate images*
# during iterative greedy selection.  Different purpose from the objective weights
# above: these drive which image to add next, not how to evaluate the final slate.
MMR_W_POPULARITY = 0.35
MMR_W_APPEAL = 0.20
MMR_W_MONTH_FIT = 0.15
MMR_W_REDUNDANCY = 0.20
MMR_W_UNCERTAINTY = 0.10

# Beta-Binomial prior for batch voting scores
BETA_PRIOR_ALPHA = 2.0
BETA_PRIOR_BETA = 8.0

# Font path overrides for calendar rendering (render/layout.py)
FONT_REGULAR = os.environ.get("ARTEMIS_FONT_REGULAR", "")
FONT_BOLD = os.environ.get("ARTEMIS_FONT_BOLD", "")
FONT_LIGHT = os.environ.get("ARTEMIS_FONT_LIGHT", "")
