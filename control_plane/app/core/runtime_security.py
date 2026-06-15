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
        raise RuntimeError(
            "PUBLIC_EXPOSURE=true requires a strong ADMIN_TOKEN with at least 24 chars and mixed classes"
        )

    if settings.deployment_mode == "saas":
        # 1. Require even stronger ADMIN_TOKEN for SaaS
        if len(settings.admin_token) < 32 or not is_strong_admin_token(settings.admin_token):
            raise RuntimeError(
                "DEPLOYMENT_MODE=saas requires a VERY strong ADMIN_TOKEN (min 32 chars and mixed classes)"
            )

        # 2. Require explicit CORS_ALLOW_ORIGINS
        if not settings.cors_allow_origins or "*" in settings.cors_allow_origins:
            raise RuntimeError(
                "DEPLOYMENT_MODE=saas requires explicit CORS_ALLOW_ORIGINS (wildcard '*' or empty NOT allowed)"
            )

        # 3. Require PUBLIC_EXPOSURE if it's SaaS (usually it is, but let's be explicit if needed)
        # Actually, let's just enforce the other constraints.
