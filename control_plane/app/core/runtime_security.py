from __future__ import annotations

import re

from app.core.config import Settings


def is_strong_admin_token(token: str) -> bool:
    if len(token) < 24 or token == "change-this-admin-token":
        return False
    classes = 0
    classes += bool(re.search(r"[a-z]", token))
    classes += bool(re.search(r"[A-Z]", token))
    classes += bool(re.search(r"[0-9]", token))
    classes += bool(re.search(r"[^A-Za-z0-9]", token))
    return classes >= 3


def validate_runtime_security(settings: Settings) -> None:
    if settings.public_exposure and not is_strong_admin_token(settings.admin_token):
        raise RuntimeError("PUBLIC_EXPOSURE=true requires a strong ADMIN_TOKEN with at least 24 chars and mixed classes")
