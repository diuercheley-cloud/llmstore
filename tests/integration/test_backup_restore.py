import pytest
from app.schemas.backup import BackupManifest
from app.services.backup.backup_service import BackupService


@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)


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
    res = await service.verify_backup(manifest.backup_id)
    assert res.status == "valid"

    # Tamper with a component hash
    manifest.components[0].data_hash = "tampered_hash_value"

    # Save the tampered manifest back
    manifest_path = service.backup_root / manifest.backup_id / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")

    # Verify should detect corruption
    res_tampered = await service.verify_backup(manifest.backup_id)
    assert res_tampered.status == "corrupted"
    assert any(c.status == "mismatch" for c in res_tampered.component_verification)


@pytest.mark.asyncio
async def test_restore_dry_run_safety(session):
    service = BackupService(session)
    manifest = await service.create_backup()

    from app.schemas.backup import BackupRestoreRequest

    res = await service.restore_backup(manifest.backup_id, BackupRestoreRequest(dry_run=True))
    assert res.status == "dry_run_complete"
    assert res.details["side_effects_prevented"] is True
    assert len(res.plan) == len(manifest.components)


def test_backup_manifest_redaction():

    manifest = BackupManifest(
        encryption_status="redacted",
        archive_checksum="mock-checksum",
        payload_file="mock-payload",
        payload_signature="mock-signature",
    )
    assert manifest.encryption_status == "redacted"


@pytest.mark.asyncio
async def test_backup_api_flow(admin_client, session):
    from app.core.config import get_settings

    settings = get_settings()
    settings.backup_restore_enabled = True
    token = settings.admin_super_token or settings.admin_token or "test-admin-token"
    headers = {"X-Admin-Token": token}

    # 1. Create
    resp = await admin_client.post("/admin/backup/create", headers=headers)
    assert resp.status_code == 200
    backup_id = resp.json()["backup_id"]

    # 2. List
    resp_list = await admin_client.get("/admin/backup/list", headers=headers)
    assert resp_list.status_code == 200
    assert any(b["id"] == backup_id for b in resp_list.json())

    # 3. Verify
    resp_verify = await admin_client.post(f"/admin/backup/{backup_id}/verify", headers=headers)
    assert resp_verify.status_code == 200
    assert resp_verify.json()["status"] == "valid"

    # 4. Dry-run Restore
    resp_restore = await admin_client.post(
        f"/admin/backup/{backup_id}/restore/dry-run", headers=headers
    )
    assert resp_restore.status_code == 200
    assert resp_restore.json()["details"]["side_effects_prevented"] is True
