import pytest
from app.services.operations.reproducible_builds.reproducible_build_service import (
    ReproducibleBuildService,
)


def _payload():
    return {
        "client_id": "tenant-a",
        "build_name": "plugin-build",
        "build_scope": "plugin",
        "source_reference": "plugins/example",
        "deterministic_version": "v1",
        "build_environment_hash": "a" * 64,
        "reproducibility_status": "proposed",
        "replay_safe": True,
    }


def test_create_and_validate_build_manifest():
    service = ReproducibleBuildService()
    manifest = service.create_build_manifest(_payload())
    validation = service.validate_build_manifest(manifest)
    assert manifest.replay_safe is True
    assert validation["valid"] is True
    assert validation["reproducibility_status"] == "reproducible"


def test_revoke_build_manifest():
    service = ReproducibleBuildService()
    manifest = service.create_build_manifest(_payload())
    revocation = service.revoke_build_manifest(manifest)
    assert revocation["status"] == "revoked"
    assert manifest.replay_safe is False


def test_build_manifest_requires_replay_safe():
    service = ReproducibleBuildService()
    payload = _payload()
    payload["replay_safe"] = False
    with pytest.raises(ValueError):
        service.create_build_manifest(payload)
