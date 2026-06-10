from app.services.operations.plugin_supply_chain.hash_utils import (
    canonical_json,
    compute_lineage_hash,
    compute_provenance_hash,
    compute_sbom_hash,
    sha256_hex,
)


def test_plugin_supply_chain_hashes_are_deterministic():
    payload = {"b": 2, "a": 1, "created_at": "2026-05-16T00:00:00Z"}
    assert canonical_json(payload) == '{"a":1,"b":2}'
    assert sha256_hex(payload) == sha256_hex({"a": 1, "b": 2})
    assert compute_provenance_hash({"x": 1}) == compute_provenance_hash({"x": 1})
    assert compute_sbom_hash({"x": 1}) == compute_sbom_hash({"x": 1})
    assert compute_lineage_hash({"x": 1}) == compute_lineage_hash({"x": 1})
