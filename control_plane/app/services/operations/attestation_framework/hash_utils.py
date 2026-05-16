import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

LOGICAL_TIMESTAMP_KEYS = {
    "created_at",
    "updated_at",
    "generated_at",
    "verified_at",
    "revoked_at",
    "imported_at",
    "exported_at",
    "timestamp",
}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            if key in LOGICAL_TIMESTAMP_KEYS:
                continue
            normalized[key] = _normalize_value(value[key])
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        return [_normalize_value(item) for item in sorted(value, key=lambda item: json.dumps(_normalize_value(item), sort_keys=True, ensure_ascii=False))]
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def canonical_json(data: Any) -> str:
    return json.dumps(
        _normalize_value(data),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def sha256_hex(data: Any) -> str:
    raw = data if isinstance(data, str) else canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_attestation_hash(payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "attestation", **payload})


def compute_bundle_hash(bundle_payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "federation_bundle", **bundle_payload})


def compute_chain_link_hash(link_payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "chain_link", **link_payload})
