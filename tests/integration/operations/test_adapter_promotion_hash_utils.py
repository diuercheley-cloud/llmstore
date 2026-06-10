from app.services.operations.adapter_promotion.hash_utils import (
    canonical_json,
    compute_gate_hash,
    compute_promotion_hash,
    compute_transition_hash,
    sha256_hex,
)


def test_canonical_json():
    data = {"b": 2, "a": 1}
    assert canonical_json(data) == '{"a": 1, "b": 2}'

def test_sha256_hex():
    res = sha256_hex("test")
    assert len(res) == 64
    assert res == sha256_hex("test")

def test_hashes_are_deterministic():
    payload = {"foo": "bar"}
    h1 = compute_promotion_hash(payload)
    h2 = compute_promotion_hash(payload)
    assert h1 == h2

    g1 = compute_gate_hash(payload)
    g2 = compute_gate_hash(payload)
    assert g1 == g2

    t1 = compute_transition_hash(payload)
    t2 = compute_transition_hash(payload)
    assert t1 == t2
