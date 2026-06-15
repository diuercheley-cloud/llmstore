# bootstrap/observability.py

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security


def setup_observability():
    configure_logging()
    settings = get_settings()
    validate_runtime_security(settings)
