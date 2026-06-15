from app.services.operations.reproducible_builds.artifact_verification import (
    ArtifactVerificationService,
)
from app.services.operations.reproducible_builds.lineage_service import SourceArtifactLineageService
from app.services.operations.reproducible_builds.replay_verifier import ArtifactReplayVerifier
from app.services.operations.reproducible_builds.reproducible_build_service import (
    ReproducibleBuildService,
)


def test_artifact_replay_verifier():
    build_service = ReproducibleBuildService()
    manifest = build_service.create_build_manifest(
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
    artifact_service = ArtifactVerificationService()
    record = artifact_service.verify_artifact(
        manifest, {"artifact_name": "bundle", "artifact_version": "1.0.0", "artifact_payload": {}}
    )
    lineage = SourceArtifactLineageService().create_lineage(
        manifest, "b" * 64, record.artifact_hash
    )
    verifier = ArtifactReplayVerifier()
    assert verifier.replay_build_manifest(manifest)["match"] is True
    assert verifier.replay_artifact(record)["match"] is True
    assert verifier.replay_lineage(lineage)["match"] is True
