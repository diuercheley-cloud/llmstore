import hashlib
import json
from typing import Any

def canonical_json(data: Any) -> str:
    """Returns a canonical JSON string representation of the data."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)

def sha256_hex(data: str) -> str:
    """Computes SHA-256 hash of a string and returns it in hex format."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def compute_registry_hash(entry_payload: dict, version: str = "v1") -> str:
    """Computes a deterministic registry hash for an entry payload."""
    # Exclude non-logical fields like timestamps or ephemeral IDs if needed
    # For now, we use the canonical JSON of the payload
    return sha256_hex(f"{version}:{canonical_json(entry_payload)}")

def compute_policy_hash(policy_payload: dict, version: str = "v1") -> str:
    """Computes a deterministic policy hash for a policy payload."""
    return sha256_hex(f"{version}:{canonical_json(policy_payload)}")
