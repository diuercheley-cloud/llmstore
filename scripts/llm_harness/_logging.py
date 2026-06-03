import json
import logging
import os
import sys
from datetime import UTC, datetime

from .sanitizer import Sanitizer


class StructuredLogger(logging.Handler):
    """JSON structured log handler that writes to stderr.

    Emits log entries as single-line JSON objects with correlation IDs
    and automatic secret redaction.
    """

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": Sanitizer.sanitize_text(record.getMessage()),
            "module": record.module,
        }
        # Add correlation IDs if present
        for field in ("trace_id", "task_id", "agent_id", "step_index"):
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        try:
            sys.stderr.write(json.dumps(log_entry) + "\n")
        except Exception:
            # Fallback: don't crash on serialization errors
            err_json = json.dumps({"level": "ERROR", "message": "Failed to serialize log entry"})
            sys.stderr.write(err_json + "\n")




def setup_logging(
    level: int | None = None,
    structured: bool = True,
) -> None:
    """Configure logging for the LLM Harness.

    Args:
        level: Log level. If None, reads from LOG_LEVEL env var (default: INFO).
        structured: If True, adds JSON structured handler to stderr.
    """
    if level is None:
        env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, env_level, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    if structured:
        root_logger = logging.getLogger()
        # Avoid duplicate handlers on repeated calls
        if not any(isinstance(h, StructuredLogger) for h in root_logger.handlers):
            root_logger.addHandler(StructuredLogger())
