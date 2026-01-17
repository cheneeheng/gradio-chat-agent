"""Centralized logging setup for the Gradio Chat Agent."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSONL."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "component": record.name,
        }

        # Include extra fields if provided
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Include exception info if available
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Traceability
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "project_id"):
            log_entry["project_id"] = record.project_id

        return json.dumps(log_entry)


def setup_logging(level: Optional[str] = None):
    """Initializes the logging system.

    Args:
        level: Optional log level override. Defaults to LOG_LEVEL env var or INFO.
    """
    log_level = level or os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    # Remove existing handlers to avoid duplicates
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Retrieves a logger with the given name.

    Args:
        name: The name of the logger (typically __name__).

    Returns:
        A logging.Logger instance.
    """
    return logging.getLogger(name)
