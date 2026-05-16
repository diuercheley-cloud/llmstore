from app.services.operations.plugin_runtime.hash_utils import (
    canonical_json,
    compute_abi_contract_hash,
    compute_compatibility_hash,
    compute_load_plan_hash,
    compute_replay_hash,
    sha256_hex,
)


def test_plugin_runtime_hash_utils_are_deterministic():
    payload = {"b": 2, "a": 1, "created_at": "ignored"}
    assert canonical_json(payload) == '{"a":1,"b":2}'
    assert sha256_hex(payload) == sha256_hex({"a": 1, "b": 2})
    assert compute_abi_contract_hash(payload) == compute_abi_contract_hash({"a": 1, "b": 2})
    assert compute_load_plan_hash(payload) == compute_load_plan_hash({"a": 1, "b": 2})
    assert compute_compatibility_hash(payload) == compute_compatibility_hash({"a": 1, "b": 2})
    assert compute_replay_hash(payload) == compute_replay_hash({"a": 1, "b": 2})
