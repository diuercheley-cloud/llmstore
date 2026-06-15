from app.services.operations.attestation_framework.hash_utils import (
    canonical_json,
    compute_attestation_hash,
    compute_bundle_hash,
    compute_chain_link_hash,
)


def test_hash_utils_are_deterministic():
    payload = {"b": 2, "a": 1, "created_at": "2026-05-16T00:00:00Z"}
    assert canonical_json(payload) == canonical_json({"a": 1, "b": 2})
    assert compute_attestation_hash({"payload": payload}) == compute_attestation_hash(
        {"payload": {"a": 1, "b": 2}}
    )
    assert compute_bundle_hash({"bundle": ["a", "b"]}) == compute_bundle_hash(
        {"bundle": ["a", "b"]}
    )
    assert compute_chain_link_hash({"x": 1}) == compute_chain_link_hash({"x": 1})
