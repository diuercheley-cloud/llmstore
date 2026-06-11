from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup.backup_service import BackupService
from app.services.backup.promotion import RestorePromotionService
from app.services.backup.restore_staging_service import RestoreStagingService
from tests.backup.fixtures import seed_recovery_state, collect_recovery_state, mutate_recovery_state

@pytest.mark.asyncio
async def test_restore_idempotency_sqlite(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.config import get_settings
    settings = get_settings()
    settings.database_url = sqlite_backup_db_url
    settings.disaster_recovery_backup_dir = str(backup_store_root)
    settings.backup_restore_enabled = True

    promote_calls = 0
    original_promote = RestorePromotionService.promote_database

    async def wrapped_promote(self, *args, **kwargs):
        nonlocal promote_calls
        promote_calls += 1
        return await original_promote(self, *args, **kwargs)

    monkeypatch.setattr(RestorePromotionService, "promote_database", wrapped_promote)

    async with sqlite_session_factory() as session:
        ids = await seed_recovery_state(session, backup_repo_root)
        expected = await collect_recovery_state(session, backup_repo_root, ids)
        
        service = BackupService(session)
        manifest = await service.create_backup(BackupCreateRequest(scope="full"))
        backup_id = manifest.backup_id

    # Restore 1
    async with sqlite_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)
        restore_service = RestoreStagingService(session)
        result1 = await restore_service.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False))
        assert result1.status == "restored"
        
        actual1 = await collect_recovery_state(session, backup_repo_root, ids)
        assert actual1 == expected

    # Restore 2 (Idempotency check)
    async with sqlite_session_factory() as session:
        restore_service = RestoreStagingService(session)
        result2 = await restore_service.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False))
        assert result2.status == "restored"
        
        actual2 = await collect_recovery_state(session, backup_repo_root, ids)
        assert actual2 == expected

    assert promote_calls == 1

@pytest.mark.asyncio
async def test_restore_failed_staging_idempotency(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.config import get_settings
    settings = get_settings()
    settings.database_url = sqlite_backup_db_url
    settings.disaster_recovery_backup_dir = str(backup_store_root)
    settings.backup_restore_enabled = True

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        service = BackupService(session)
        manifest = await service.create_backup(BackupCreateRequest(scope="full"))
        backup_id = manifest.backup_id

    # Mock staging validation failure
    from app.services.backup.staging import RestoreStagingService as StagingLogic
    async def mock_validate(*args, **kwargs):
        return {"valid": False, "errors": ["Simulated failure"]}
    monkeypatch.setattr(StagingLogic, "validate_staging_db", mock_validate)

    async with sqlite_session_factory() as session:
        restore_service = RestoreStagingService(session)
        result = await restore_service.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False))
        assert result.status == "failed"
        assert result.error_code == "RESTORE_STAGING_FAILED"

    # Ensure lock is released and we can try again (even if it still fails, it shouldn't be LOCKED)
    async with sqlite_session_factory() as session:
        restore_service = RestoreStagingService(session)
        result2 = await restore_service.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False))
        assert result2.status == "failed"
        assert result2.error_code == "RESTORE_STAGING_FAILED"
