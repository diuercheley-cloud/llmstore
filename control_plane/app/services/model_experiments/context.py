from contextvars import ContextVar
from typing import Any

# Context variable to store active experiment metadata for the current request
experiment_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "experiment_context", default=None
)


def set_experiment_context(metadata: dict[str, Any]):
    experiment_context.set(metadata)


def get_experiment_context() -> dict[str, Any] | None:
    return experiment_context.get()


def clear_experiment_context():
    experiment_context.set(None)
