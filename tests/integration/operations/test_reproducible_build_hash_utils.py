from app.services.operations.reproducible_builds.hash_utils import (
    canonical_json,
    compute_artifact_hash,
    compute_build_manifest_hash,
    compute_lineage_hash,
    compute_replay_hash,
)


def test_canonical_json_ignores_timestamps():
    left = canonical_json({"b": 2, "created_at": "2026-05-16T00:00:00Z", "a": 1})
    right = canonical_json({"a": 1, "b": 2, "created_at": "2026-05-16T01:00:00Z"})
    assert left == right


def test_deterministic_hashes_stable():
    payload = {"client_id": "tenant-a", "artifact": {"name": "bundle", "version": "1.0.0"}}
    assert compute_build_manifest_hash(payload) == compute_build_manifest_hash(dict(reversed(list(payload.items()))))
    assert compute_artifact_hash(payload) == compute_artifact_hash(payload)
    assert compute_lineage_hash(payload) == compute_lineage_hash(payload)
    assert compute_replay_hash(payload) == compute_replay_hash(payload)
