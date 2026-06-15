from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from app.core.config import get_settings
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup.backup_service import BackupService
from app.services.backup.database_providers import SQLiteBackupProvider
from app.services.backup.restore_staging_service import RestoreStagingService

from tests.backup_dr.fixtures import (
    collect_recovery_state,
    mutate_recovery_state,
    seed_recovery_state,
)

pytestmark = [pytest.mark.backup_dr]


def _configure_settings(database_url: str, backup_store_root: Path) -> None:
    settings = get_settings()
    settings.database_url = database_url
    settings.disaster_recovery_backup_dir = str(backup_store_root)
    settings.backup_restore_enabled = True
    settings.deployment_mode = "local"


def _backup_paths(backup_store_root: Path, backup_id: str) -> tuple[Path, Path]:
    backup_dir = backup_store_root / "system" / backup_id
    return backup_dir / "manifest.json", backup_dir / "payload.tar.gz.enc"


def _write_dr_report(engine: str, scenario: str, status: str, details: dict | None = None):
    report_dir = Path("artifacts/dr-reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"dr_report_{engine}_{scenario}.yaml"
    report = {
        "engine": engine,
        "scenario": scenario,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "details": details or {},
    }
    with open(report_file, "w") as f:
        yaml.dump(report, f)


@pytest.mark.asyncio
async def test_sqlite_full_dr_restore(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "full_restore"

    try:
        async with sqlite_session_factory() as session:
            ids = await seed_recovery_state(session, backup_repo_root)
            expected = await collect_recovery_state(session, backup_repo_root, ids)
            manifest = await BackupService(session).create_backup(
                BackupCreateRequest(scope="full"), actor="dr-bot"
            )
            backup_id = manifest.backup_id

        async with sqlite_session_factory() as session:
            await mutate_recovery_state(session, backup_repo_root, ids)

        async with sqlite_session_factory() as session:
            result = await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False), actor="dr-bot"
            )
            assert result.status == "restored"

        async with sqlite_session_factory() as session:
            actual = await collect_recovery_state(session, backup_repo_root, ids)
        assert actual == expected
        _write_dr_report(engine, scenario, "success")
    except Exception as e:
        _write_dr_report(engine, scenario, "failed", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_postgres_full_dr_restore(
    postgres_session_factory,
    postgres_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(postgres_backup_db_url, backup_store_root)
    engine = "postgres"
    scenario = "full_restore"

    try:
        async with postgres_session_factory() as session:
            ids = await seed_recovery_state(session, backup_repo_root)
            expected = await collect_recovery_state(session, backup_repo_root, ids)
            manifest = await BackupService(session).create_backup(
                BackupCreateRequest(scope="full"), actor="dr-bot"
            )
            backup_id = manifest.backup_id

        async with postgres_session_factory() as session:
            await mutate_recovery_state(session, backup_repo_root, ids)

        async with postgres_session_factory() as session:
            result = await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False), actor="dr-bot"
            )
            assert result.status == "restored"

        async with postgres_session_factory() as session:
            actual = await collect_recovery_state(session, backup_repo_root, ids)
        assert actual == expected
        _write_dr_report(engine, scenario, "success")
    except Exception as e:
        _write_dr_report(engine, scenario, "failed", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_dr_manifest_corruption(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "manifest_corruption"

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    manifest_path, _ = _backup_paths(backup_store_root, backup_id)
    manifest_path.write_text("{corrupted-json", encoding="utf-8")

    async with sqlite_session_factory() as session:
        with pytest.raises(Exception):  # Should fail during manifest load/parse
            await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )

    _write_dr_report(
        engine, scenario, "success", {"note": "Restore correctly blocked by corrupted manifest"}
    )


@pytest.mark.asyncio
async def test_dr_payload_corruption(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "payload_corruption"

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    _, payload_path = _backup_paths(backup_store_root, backup_id)
    payload = bytearray(payload_path.read_bytes())
    payload[len(payload) // 2] = (payload[len(payload) // 2] + 1) % 255
    payload_path.write_bytes(payload)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "blocked"
        assert "verification failed" in result.details.get("reason", "").lower()

    _write_dr_report(
        engine, scenario, "success", {"note": "Restore correctly blocked by corrupted payload"}
    )


@pytest.mark.asyncio
async def test_dr_path_traversal_protection(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "path_traversal"

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        service = BackupService(session)
        backup_id = (await service.create_backup(BackupCreateRequest(scope="full"))).backup_id

        # Manually corrupt payload with path traversal
        from tests.backup_dr.fixtures import _rewrite_backup_for_path_traversal as rewrite

        rewrite(service, backup_store_root, backup_id)

    async with sqlite_session_factory() as session:
        with pytest.raises(ValueError, match="Directory traversal sequence"):
            await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )

    _write_dr_report(engine, scenario, "success", {"note": "Path traversal attempt blocked"})


@pytest.mark.asyncio
async def test_dr_key_rotation_failure(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "key_loss"

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    # Change keys
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "wrong-key" * 8)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "blocked"

    _write_dr_report(engine, scenario, "success", {"note": "Restore blocked after key loss"})


@pytest.mark.asyncio
async def test_dr_rollback_on_failure(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "rollback"

    async with sqlite_session_factory() as session:
        ids = await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    async with sqlite_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)
        mutated_state = await collect_recovery_state(session, backup_repo_root, ids)

    # Force failure during promotion
    from app.services.backup.promotion import RestorePromotionService

    async def fail_promotion(*args, **kwargs):
        raise RuntimeError("DR simulated promotion failure")

    monkeypatch.setattr(RestorePromotionService, "promote_database", fail_promotion)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "failed"

        # Verify rollback - state should be what it was before restore (which was mutated_state because restore failed)
        actual = await collect_recovery_state(session, backup_repo_root, ids)
        assert actual == mutated_state

    _write_dr_report(
        engine, scenario, "success", {"note": "Rollback verified after promotion failure"}
    )


@pytest.mark.asyncio
async def test_dr_concurrency_control(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)
    engine = "sqlite"
    scenario = "concurrency"

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    # Mock restore to block
    entered = asyncio.Event()
    release = asyncio.Event()

    original_restore = SQLiteBackupProvider.restore_database

    async def slow_restore(self, src_file):
        entered.set()
        await release.wait()
        await original_restore(self, src_file)

    import unittest.mock

    with unittest.mock.patch.object(SQLiteBackupProvider, "restore_database", slow_restore):
        task1 = asyncio.create_task(
            RestoreStagingService(await sqlite_session_factory().__aenter__()).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )
        )
        await entered.wait()

        # Second attempt should be blocked
        async with sqlite_session_factory() as session:
            with pytest.raises(Exception, match="already in progress"):
                await RestoreStagingService(session).restore_with_staging(
                    backup_id, BackupRestoreRequest(dry_run=False)
                )

        release.set()
        await task1

    _write_dr_report(engine, scenario, "success", {"note": "Concurrency lock verified"})
