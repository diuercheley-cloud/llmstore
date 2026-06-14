import os
import pytest
from unittest.mock import MagicMock, patch
from app.services.backup.backup_service import BackupService
from app.schemas.backup import BackupManifest

def test_backup_service_initialization_no_keys(monkeypatch):
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("BACKUP_SIGNING_KEY", raising=False)
    
    with pytest.raises(ValueError, match="BACKUP_ENCRYPTION_KEY and BACKUP_SIGNING_KEY environment variables must be defined"):
        BackupService(None)

def test_backup_service_initialization_short_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "too_short")
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "too_short")
    
    with pytest.raises(ValueError, match="must be at least 32 characters long"):
        BackupService(None)

def test_backup_service_initialization_valid_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)
    
    # This should not raise an error
    service = BackupService(None)
    assert service.key_id is not None

@pytest.mark.asyncio
async def test_backup_service_key_id_warning(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)
    monkeypatch.setenv("BACKUP_KEY_ID", "current-key")

    from unittest.mock import AsyncMock, MagicMock
    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # db.add() is synchronous in SQLAlchemy
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None  # no previous hash
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    service = BackupService(mock_db)

    
    # Mock _read_manifest
    mock_manifest = BackupManifest(
        backup_id="test-backup",
        archive_checksum="abc",
        payload_file="payload.enc",
        payload_signature="sig",
        key_id="different-key",
        components=[]
    )
    service._read_manifest = MagicMock(return_value=mock_manifest)
    
    # Mock payload path reading and decryption
    with patch("pathlib.Path.read_bytes", return_value=b"encrypted_data"):
        service._fernet = MagicMock()
        service._fernet.decrypt.return_value = b""  # empty zip/tar bytes
        
        # We also mock tarfile.open to avoid extraction errors
        with patch("tarfile.open") as mock_tar:
            res = await service.verify_backup("test-backup")
            assert "key_id_mismatch" in res.details
            assert res.details["key_id_mismatch"] == "Expected 'different-key', current is 'current-key'"


def test_backup_create_request_compatibility():
    from app.schemas.backup import BackupCreateRequest
    
    # 1. Default creation values
    req = BackupCreateRequest()
    assert req.scope == "logical-agent-backup"
    
    # 2. Legacy full=True request
    req_legacy = BackupCreateRequest(full=True)
    assert req_legacy.full is True


@pytest.mark.asyncio
async def test_backup_restore_compatibility_full_scope(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)

    from unittest.mock import AsyncMock
    service = BackupService(None)
    
    # Mock reading a manifest with scope="full"
    mock_manifest = BackupManifest(
        backup_id="legacy-backup",
        scope="full",
        archive_checksum="abc",
        payload_file="payload.enc",
        payload_signature="sig",
        components=[]
    )
    service._read_manifest = MagicMock(return_value=mock_manifest)
    from app.schemas.backup import BackupVerificationResult
    service.verify_backup = AsyncMock(return_value=BackupVerificationResult(
        backup_id="legacy-backup",
        status="valid",
        signature_valid=True,
        archive_checksum_valid=True,
        component_verification=[]
    ))
    import tempfile
    from pathlib import Path
    from sqlalchemy import create_engine
    from app.db.base import Base
    import app.models
    
    # Generate a valid SQLite database file with all tables for testing
    tmp_db = tempfile.mktemp()
    sync_engine = create_engine(f"sqlite:///{tmp_db}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    
    valid_db_bytes = Path(tmp_db).read_bytes()
    try:
        os.remove(tmp_db)
    except Exception:
        pass

    service._extract_payload_parts = MagicMock(return_value={
        "database.json": {"tables": {}},
        "configs.json": {"files": []},
        "feature_flags.json": {},
        "db.dump": valid_db_bytes
    })
    service._restore_database = AsyncMock()
    service._restore_configs = MagicMock()
    service._restore_feature_flags = MagicMock()
    mock_db_svc = AsyncMock()
    mock_db_svc.add = MagicMock()  # db.add() is synchronous in SQLAlchemy
    service.db = mock_db_svc

    service.create_backup = AsyncMock(return_value=BackupManifest(
        backup_id="safety-backup",
        scope="full",
        archive_checksum="xyz",
        payload_file="payload-safety.enc",
        payload_signature="sig-safety",
        components=[]
    ))

    res = await service.restore_backup("legacy-backup")
    assert res.status == "restored"
