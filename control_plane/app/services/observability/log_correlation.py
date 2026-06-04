# Owner: agent-platform
import logging
import uuid
from typing import Optional


class LogCorrelationService:
    """
    Ensures logs are correlated with run and trace IDs.
    """
    @staticmethod
    def get_logger(name: str, run_id: Optional[uuid.UUID] = None, trace_id: Optional[str] = None):
        logger = logging.getLogger(name)
        extra = {}
        if run_id:
            extra["run_id"] = str(run_id)
        if trace_id:
            extra["trace_id"] = trace_id
            
        return logging.LoggerAdapter(logger, extra)

    @staticmethod
    def format_log(message: str, run_id: Optional[uuid.UUID] = None) -> str:
        prefix = f"[Run: {run_id}] " if run_id else ""
        return f"{prefix}{message}"
