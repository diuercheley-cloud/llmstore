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
    "completed_at",
    "started_at",
    "timestamp",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in sorted(value.items())
            if key not in LOGICAL_TIMESTAMP_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, set):
        normalized = [_normalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
            ),
        )
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def canonical_json(data: Any) -> str:
    return json.dumps(
        _normalize(data), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def sha256_hex(data: Any) -> str:
    raw = data if isinstance(data, str) else canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_contract_hash(payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "compatibility_contract", **payload})


def compute_matrix_hash(payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "compatibility_matrix", **payload})


def compute_negotiation_hash(payload: dict[str, Any]) -> str:
    return sha256_hex({"kind": "compatibility_negotiation", **payload})
