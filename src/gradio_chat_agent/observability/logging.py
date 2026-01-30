"""Centralized logging setup for the Gradio Chat Agent."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSONL."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically identify standard LogRecord attributes to exclude them from 'extra' fields
        dummy_record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", None, None)
        self._reserved_attrs = set(dummy_record.__dict__.keys())
        # Also exclude common attributes added by formatters or expected in the output envelope
        self._reserved_attrs.update({"message", "asctime", "stack_info"})

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "component": record.name,
        }

        # Include exception info if available
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields. We check for a designated 'extra_fields' dict
        # and also collect any other custom attributes attached to the record.
        for key, value in record.__dict__.items():
            if key not in self._reserved_attrs:
                if key == "extra_fields" and isinstance(value, dict):
                    log_entry.update(value)
                else:
                    log_entry[key] = value

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
