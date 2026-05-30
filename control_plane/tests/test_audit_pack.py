import pytest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from app.services.compliance.audit_pack import AuditPackService

@pytest.fixture
def audit_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_audit_pack_generates_files(audit_db, tmp_path):
    # Setup mock data
    mock_ev = MagicMock()
    mock_ev.id = "ev-1"
    mock_ev.evidence_type = "access_review"
    mock_ev.title = "Review Q1"
    mock_ev.summary = "All good"
    mock_ev.collected_at = None
    mock_ev.evidence_json = {"user": "admin", "api_key": "secret123"}
    
    # Mock attestations to avoid MagicMock serialization error
    mock_att = MagicMock()
    mock_att.id = "att-1"
    mock_att.control_policy_id = "pol-1"
    mock_att.attested_by = "John Doe"
    mock_att.status = "completed"
    mock_att.attestation_period_start = "2026-01-01"
    mock_att.attestation_period_end = "2026-03-31"

    mock_res_ev = MagicMock()
    mock_res_ev.scalars.return_value.all.return_value = [mock_ev]
    
    mock_res_att = MagicMock()
    mock_res_att.scalars.return_value.all.return_value = [mock_att]

    audit_db.execute.side_effect = [mock_res_ev, mock_res_att]
    
    svc = AuditPackService(audit_db)
    svc.base_path = tmp_path / "audit-packs"
    
    manifest = await svc.generate_pack("soc2")
    
    assert manifest["standard"] == "soc2"
    assert manifest["evidence_count"] >= 1
    
    # Check if files were saved
    pack_dir = svc.base_path / "soc2" / manifest["pack_id"]
    assert os.path.exists(pack_dir / "manifest.json")
    
    # Check sanitization
    with open(pack_dir / f"op_{mock_ev.id}.json", "r") as f:
        data = json.load(f)
        assert data["content"]["user"] == "admin"
        assert "api_key" not in data["content"]

@pytest.mark.asyncio
async def test_audit_pack_hash_generation(audit_db):
    svc = AuditPackService(audit_db)
    data = [{"test": 1}, {"test": 2}]
    hash1 = svc._calculate_hash(data)
    hash2 = svc._calculate_hash(data)
    assert hash1 == hash2
    
    data2 = [{"test": 1}, {"test": 3}]
    hash3 = svc._calculate_hash(data2)
    assert hash1 != hash3
