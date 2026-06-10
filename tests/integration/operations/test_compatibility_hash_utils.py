from app.services.operations.compatibility_contracts.hash_utils import (
    canonical_json,
    compute_contract_hash,
    compute_matrix_hash,
    compute_negotiation_hash,
    sha256_hex,
)


def test_hash_utils_are_deterministic():
    payload = {"b": 2, "a": 1, "created_at": "ignored"}
    assert canonical_json(payload) == '{"a":1,"b":2}'
    assert sha256_hex(payload) == sha256_hex({"a": 1, "b": 2})
    assert compute_contract_hash(payload) == compute_contract_hash({"a": 1, "b": 2})
    assert compute_matrix_hash(payload) == compute_matrix_hash({"a": 1, "b": 2})
    assert compute_negotiation_hash(payload) == compute_negotiation_hash({"a": 1, "b": 2})
