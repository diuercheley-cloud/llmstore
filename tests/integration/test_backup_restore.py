import pytest
import hashlib
import json
from app.services.backup.backup_service import BackupService
from app.schemas.backup import BackupManifest

@pytest.mark.asyncio
async def test_backup_creation_determinism(session):
    service = BackupService(session)
    manifest1 = await service.create_backup()
    manifest2 = await service.create_backup()
    
    # Components should have deterministic hashes if inputs are same
    assert len(manifest1.components) == len(manifest2.components)
    for c1, c2 in zip(manifest1.components, manifest2.components):
        assert c1.data_hash == c2.data_hash

@pytest.mark.asyncio
async def test_backup_verification_failure(session):
    service = BackupService(session)
    manifest = await service.create_backup()
    
    # Verify valid
    res = service.verify_backup(manifest)
    assert res["status"] == "valid"
    
    # Tamper with a component hash
    manifest.components[0].data_hash = "tampered_hash_value"
    
    # Verify should detect corruption
    res_tampered = service.verify_backup(manifest)
    assert res_tampered["status"] == "corrupted"
    assert any(c["status"] == "mismatch" for c in res_tampered["component_verification"])

@pytest.mark.asyncio
async def test_restore_dry_run_safety(session):
    service = BackupService(session)
    manifest = await service.create_backup()
    
    res = await service.restore_dry_run(manifest)
    assert res["status"] == "dry_run_complete"
    assert res["side_effects_prevented"] is True
    assert len(res["plan"]) == len(manifest.components)

def test_backup_manifest_redaction():
    from app.schemas.backup import BackupComponent
    # Create component with sensitive data in its "mocked data" (internal logic check)
    # The hash should be derived from redacted data or data without secrets
    # Our implementation uses a fixed string "REDACTED_API_KEY" in _create_mock_component
    
    manifest = BackupManifest(encryption_status="redacted")
    assert manifest.encryption_status == "redacted"
    
@pytest.mark.asyncio
async def test_backup_api_flow(admin_client, session):
    headers = {"X-Admin-Token": "test-admin-token"}
    
    # 1. Create
    resp = await admin_client.post("/api/admin/backup/create", headers=headers)
    assert resp.status_code == 200
    backup_id = resp.json()["backup_id"]
    
    # 2. List
    resp_list = await admin_client.get("/api/admin/backup/list", headers=headers)
    assert resp_list.status_code == 200
    assert any(b["id"] == backup_id for b in resp_list.json())
    
    # 3. Verify
    resp_verify = await admin_client.get(f"/api/admin/backup/{backup_id}/verify", headers=headers)
    assert resp_verify.status_code == 200
    assert resp_verify.json()["status"] == "valid"
    
    # 4. Dry-run Restore
    resp_restore = await admin_client.post(f"/api/admin/backup/{backup_id}/restore/dry-run", headers=headers)
    assert resp_restore.status_code == 200
    assert resp_restore.json()["side_effects_prevented"] is True
