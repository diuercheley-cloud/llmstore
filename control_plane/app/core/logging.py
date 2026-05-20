import json
import logging
import sys

from app.core.config import get_settings
from app.core.request_context import get_correlation_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if hasattr(record, "extra_data"):
            payload.update(record.extra_data)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Ignore GET /health 200 OK logs
        msg = record.getMessage()
        if "/health" in msg and ("200" in msg or "200 OK" in msg):
            return False
        return True


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    # Apply health-check filter
    handler.addFilter(HealthCheckFilter())
    
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # 1. Disable duplicated uvicorn.access logs since middleware provides rich structured logging
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False
    uvicorn_access.setLevel(logging.WARNING)

    # 4. Silence HTTPX logs unless they are WARNING or higher
    logging.getLogger("httpx").setLevel(logging.WARNING)

