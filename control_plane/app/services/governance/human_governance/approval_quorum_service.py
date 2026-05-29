from __future__ import annotations

import json


def normalize_roles(roles: list[str]) -> str:
    normalized = sorted({role.strip() for role in roles if role and role.strip()})
    return json.dumps(normalized)
