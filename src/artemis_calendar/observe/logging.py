"""Structured logging for pipeline observability."""

import json
import logging
import sys
from datetime import UTC, datetime

from artemis_calendar.config.settings import LOG_DIR


class StructuredFormatter(logging.Formatter):
    """JSON formatter with UTC timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        for key in ("run_id", "dataset_name", "pipeline_name", "source_name", "guid"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with structured JSON output to both stdout and file."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = StructuredFormatter()

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"collect_{datetime.now(UTC).strftime('%Y-%m-%d_%H%M%S')}.jsonl"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.setLevel(level)
    return logger
