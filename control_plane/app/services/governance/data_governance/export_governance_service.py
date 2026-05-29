from __future__ import annotations

import hashlib


def build_export_hash(tenant_id: str, export_type: str, encrypted: bool, mode: str) -> str:
    payload = f"{tenant_id}:{export_type}:{int(encrypted)}:{mode}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
