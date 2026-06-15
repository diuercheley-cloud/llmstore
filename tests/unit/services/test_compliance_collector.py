import os
import zipfile

import pytest
from app.services.compliance_evidence_collector import ComplianceEvidenceCollectorService


@pytest.mark.asyncio
async def test_evidence_collection_sanitization(db_session):
    # Create a dummy file with a secret
    test_file = "test_evidence.txt"
    with open(test_file, "w") as f:
        f.write("This is a PRIVATE KEY and some RAG prompt data.")

    service = ComplianceEvidenceCollectorService(
        db_session, base_artifact_dir="artifacts/test_compliance"
    )
    sanitized = service._read_and_sanitize(test_file)

    assert "[REDACTED]" in sanitized
    assert "PRIVATE KEY" not in sanitized
    assert "RAG" not in sanitized

    os.remove(test_file)


@pytest.mark.asyncio
async def test_package_generation(db_session):
    service = ComplianceEvidenceCollectorService(
        db_session, base_artifact_dir="artifacts/test_compliance"
    )

    # Manually add a file
    with open("artifacts/test_compliance/dummy.txt", "w") as f:
        f.write("test data")

    zip_path = await service.generate_package()
    assert os.path.exists(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zipf:
        assert "dummy.txt" in zipf.namelist()
