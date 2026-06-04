import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Returns a canonical JSON string representation of the data."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)

def sha256_hex(data: str) -> str:
    """Computes SHA-256 hash of a string and returns it in hex format."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def compute_promotion_hash(payload: dict, version: str = "v1") -> str:
    """Computes a deterministic promotion hash for a payload."""
    return sha256_hex(f"{version}:{canonical_json(payload)}")

def compute_gate_hash(payload: dict, version: str = "v1") -> str:
    """Computes a deterministic gate result hash."""
    return sha256_hex(f"{version}:gate:{canonical_json(payload)}")

def compute_transition_hash(payload: dict, version: str = "v1") -> str:
    """Computes a deterministic transition hash."""
    return sha256_hex(f"{version}:transition:{canonical_json(payload)}")
