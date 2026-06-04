from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context variable to store active experiment metadata for the current request
experiment_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("experiment_context", default=None)

def set_experiment_context(metadata: Dict[str, Any]):
    experiment_context.set(metadata)

def get_experiment_context() -> Optional[Dict[str, Any]]:
    return experiment_context.get()

def clear_experiment_context():
    experiment_context.set(None)
