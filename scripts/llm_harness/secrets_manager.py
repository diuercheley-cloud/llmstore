import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SECRET_NAMES: list[str] = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "LLM_BASE_URL",
    "HUGGINGFACE_TOKEN",
    "GITHUB_TOKEN",
]


class Secret:
    def __init__(self, value: str, name: str = ""):
        self._value = value
        self._name = name

    def resolve(self) -> str:
        return self._value

    def __str__(self) -> str:
        return "<redacted>"

    def __repr__(self) -> str:
        return f"Secret(name='{self._name}')"


def get_secret(name: str, default: Optional[str] = None) -> Optional[Secret]:
    value = os.environ.get(name)
    if value is not None:
        return Secret(value, name=name)
    return Secret(default, name=name) if default is not None else None


def get_required_secret(name: str) -> Secret:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Required secret '{name}' is not set")
    return Secret(value, name=name)


def list_available_secrets() -> list[str]:
    return [name for name in DEFAULT_SECRET_NAMES if os.environ.get(name)]
