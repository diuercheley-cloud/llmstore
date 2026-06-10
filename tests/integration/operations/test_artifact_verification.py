from types import SimpleNamespace

from app.services.operations.reproducible_builds.artifact_verification import (
    ArtifactVerificationService,
)


def _manifest():
    return SimpleNamespace(client_id="tenant-a", id="m" * 64, source_reference="plugins/example")


def test_verify_artifact_and_replay():
    service = ArtifactVerificationService()
    record = service.verify_artifact(
        _manifest(),
        {"artifact_name": "bundle", "artifact_version": "1.0.0", "artifact_payload": {"files": ["a.py"]}},
    )
    replay = service.validate_artifact_replay(record)
    assert record.verification_status == "passed"
    assert replay.replay_status == "passed"


def test_verify_artifact_blocks_mismatch():
    service = ArtifactVerificationService()
    record = service.verify_artifact(
        _manifest(),
        {
            "artifact_name": "bundle",
            "artifact_version": "1.0.0",
            "artifact_payload": {"files": ["a.py"]},
            "expected_hash": "f" * 64,
        },
    )
    assert record.verification_status == "blocked"
