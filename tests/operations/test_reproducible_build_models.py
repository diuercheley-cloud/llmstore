import pytest
from sqlalchemy import select

from app.models.client import Client
from app.models.operations.reproducible_builds import (
    ArtifactReplayVerification,
    ArtifactVerificationRecord,
    BuildEnvironmentConstraint,
    ReproducibilityVerificationResult,
    ReproducibleBuildManifest,
    ReproducibleBuildReceipt,
    SourceArtifactLineage,
)


def test_reproducible_build_models_exposed():
    assert ReproducibleBuildManifest.__tablename__ == "reproducible_build_manifests"
    assert ArtifactVerificationRecord.__tablename__ == "artifact_verification_records"
    assert SourceArtifactLineage.__tablename__ == "source_artifact_lineage"
    assert BuildEnvironmentConstraint.__tablename__ == "build_environment_constraints"
    assert ReproducibilityVerificationResult.__tablename__ == "reproducibility_verification_results"
    assert ArtifactReplayVerification.__tablename__ == "artifact_replay_verifications"
    assert ReproducibleBuildReceipt.__tablename__ == "reproducible_build_receipts"


@pytest.mark.asyncio
async def test_reproducible_build_models_persist(session):
    client = Client(name="phase81-models")
    session.add(client)
    await session.flush()
    manifest = ReproducibleBuildManifest(
        id="a" * 64,
        client_id=client.id,
        build_name="plugin-build",
        build_scope="plugin",
        source_reference="plugins/example",
        deterministic_version="v1",
        build_environment_hash="b" * 64,
        build_manifest_hash="c" * 64,
        reproducibility_status="proposed",
        replay_safe=True,
        immutable_hash="d" * 64,
    )
    session.add(manifest)
    await session.commit()
    stored = (await session.execute(select(ReproducibleBuildManifest))).scalar_one()
    assert stored.build_name == "plugin-build"
    assert stored.replay_safe is True


def test_phase_81_migration_present():
    content = open("control_plane/alembic/versions/phase81_reproducible_build_artifact_verification.py", "r", encoding="utf-8").read()
    assert "reproducible_build_manifests" in content
    assert "artifact_verification_records" in content
    assert "_uuid_type" in content
