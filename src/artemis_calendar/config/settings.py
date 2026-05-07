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
