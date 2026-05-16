from app.services.operations.federation_sync.hash_utils import (
    canonical_json,
    compute_bundle_hash,
    compute_lineage_hash,
    compute_negotiation_hash,
    compute_session_hash,
)


def test_federation_hash_utils_deterministic():
    data = {"b": 2, "a": 1, "created_at": "ignored"}
    assert canonical_json(data) == '{"a":1,"b":2}'
    assert compute_session_hash(data) == compute_session_hash({"a": 1, "b": 2})
    assert compute_bundle_hash(data) == compute_bundle_hash({"a": 1, "b": 2})
    assert compute_lineage_hash(data) == compute_lineage_hash({"a": 1, "b": 2})
    assert compute_negotiation_hash(data) == compute_negotiation_hash({"a": 1, "b": 2})
