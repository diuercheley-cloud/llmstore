from types import SimpleNamespace

from app.models.operations.reproducible_builds import ReproducibilityVerificationResult
from app.services.operations.reproducible_builds.receipts import (
    build_artifact_receipt,
    build_lineage_receipt,
    build_manifest_receipt,
    build_reproducibility_receipt,
)
from app.services.operations.reproducible_builds.reproducible_build_service import (
    ReproducibleBuildService,
)


def _manifest():
    return ReproducibleBuildService().create_build_manifest(
        {
            "client_id": "tenant-a",
            "build_name": "plugin-build",
            "build_scope": "plugin",
            "source_reference": "plugins/example",
            "deterministic_version": "v1",
            "build_environment_hash": "a" * 64,
            "replay_safe": True,
        }
    )


def test_receipts_contain_required_fields():
    manifest = _manifest()
    artifact = SimpleNamespace(id="a" * 64, artifact_hash="b" * 64)
    lineage = SimpleNamespace(id="c" * 64, lineage_hash="d" * 64)
    verification = ReproducibilityVerificationResult(
        id="e" * 64,
        client_id=manifest.client_id,
        build_manifest_id=manifest.id,
        verification_type="hash_replay",
        verification_status="passed",
        replay_safe=True,
        reproducibility_summary="{}",
        immutable_hash="f" * 64,
    )
    receipts = [
        build_manifest_receipt(manifest),
        build_artifact_receipt(manifest, artifact),
        build_lineage_receipt(manifest, lineage),
        build_reproducibility_receipt(manifest, verification),
    ]
    for receipt in receipts:
        assert receipt.receipt_type
        assert receipt.payload_hash
        assert isinstance(receipt.signature, str) and len(receipt.signature) > 0
