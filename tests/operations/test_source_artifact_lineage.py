from types import SimpleNamespace

from app.services.operations.reproducible_builds.lineage_service import SourceArtifactLineageService


def _manifest():
    return SimpleNamespace(client_id="tenant-a", id="m" * 64, source_reference="plugins/example")


def test_lineage_verification_and_integrity():
    service = SourceArtifactLineageService()
    lineage = service.create_lineage(_manifest(), "a" * 64, "b" * 64)
    verification = service.verify_lineage(lineage)
    integrity = service.validate_lineage_integrity(lineage, "b" * 64)
    assert verification["verified"] is True
    assert integrity["integrity_ok"] is True


def test_lineage_conflict_blocks():
    service = SourceArtifactLineageService()
    lineage = service.create_lineage(_manifest(), "a" * 64, "b" * 64)
    integrity = service.validate_lineage_integrity(lineage, "c" * 64)
    assert integrity["verification_status"] == "blocked"
