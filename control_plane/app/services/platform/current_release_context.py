import os
from pathlib import Path
from typing import Any


def get_current_tag() -> str:
    # Check env first
    tag = os.getenv("TAG") or os.getenv("RELEASE_TAG")
    if tag:
        return tag.strip()

    # Try to find VERSION file in parent dirs
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        vfile = parent / "VERSION"
        if vfile.exists():
            return vfile.read_text(encoding="utf-8").strip()

    # Fallback to local default
    return "v2.0.2-agentic-ga-readiness"


def get_current_release_context() -> dict[str, Any]:
    tag = get_current_tag()
    is_production = any(keyword in tag for keyword in ["production", "agentic", "platform"])
    return {
        "tag": tag,
        "is_production": is_production,
        "environment": "production" if is_production else "development",
    }
