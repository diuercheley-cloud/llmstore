from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup.backup_service import BackupService, _sha256_bytes
from app.services.backup.database_providers import SQLiteBackupProvider
from app.services.backup.restore_staging_service import RestoreStagingService
from fastapi import HTTPException

from tests.backup.fixtures import collect_recovery_state, mutate_recovery_state, seed_recovery_state

pytestmark = [pytest.mark.integration]


def _configure_settings(database_url: str, backup_store_root: Path) -> None:
    settings = get_settings()
    settings.database_url = database_url
    settings.disaster_recovery_backup_dir = str(backup_store_root)
    settings.backup_restore_enabled = True
    settings.deployment_mode = "local"


def _backup_paths(backup_store_root: Path, backup_id: str) -> tuple[Path, Path]:
    backup_dir = backup_store_root / "system" / backup_id
    return backup_dir / "manifest.json", backup_dir / "payload.tar.gz.enc"


def _rewrite_backup_for_path_traversal(
    service: BackupService, backup_store_root: Path, backup_id: str
) -> None:
    manifest = service._read_manifest(backup_id)
    _, payload_path = _backup_paths(backup_store_root, backup_id)
    archive_bytes = service._fernet.decrypt(payload_path.read_bytes())
    parts = service._extract_payload_parts(backup_id, manifest)
    parts["configs.json"]["files"][0]["path"] = "../escape.txt"
    parts["configs.json"] = json.dumps(parts["configs.json"], sort_keys=True).encode("utf-8")
    parts["feature_flags.json"] = json.dumps(parts["feature_flags.json"], sort_keys=True).encode(
        "utf-8"
    )
    archive_bytes = service._build_archive(parts)
    encrypted_payload = service._fernet.encrypt(archive_bytes)
    payload_path.write_bytes(encrypted_payload)

    for component in manifest.components:
        payload = parts[component.file_name]
        if isinstance(payload, dict):
            payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        component.data_hash = _sha256_bytes(payload)
    manifest.archive_checksum = _sha256_bytes(encrypted_payload)
    manifest.payload_signature = service._sign_payload(
        {
            "backup_id": manifest.backup_id,
            "archive_checksum": manifest.archive_checksum,
            "components": [component.model_dump() for component in manifest.components],
        }
    )
    manifest_path, _ = _backup_paths(backup_store_root, backup_id)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_sqlite_full_restore_recovers_all_required_domains(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        ids = await seed_recovery_state(session, backup_repo_root)
        expected = await collect_recovery_state(session, backup_repo_root, ids)

    async with sqlite_session_factory() as session:
        manifest = await BackupService(session).create_backup(
            BackupCreateRequest(scope="full"), actor="sqlite-dr"
        )
        assert manifest.scope == "full"
        assert manifest.coverage == "full"
        assert manifest.excluded == []
        backup_id = manifest.backup_id

    async with sqlite_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id,
            BackupRestoreRequest(dry_run=False),
            actor="sqlite-dr",
        )
        assert result.status == "restored"

    async with sqlite_session_factory() as session:
        actual = await collect_recovery_state(session, backup_repo_root, ids)
    assert actual == expected


@pytest.mark.asyncio
async def test_sqlite_restore_blocks_when_payload_is_corrupted(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        manifest = await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        backup_id = manifest.backup_id

    _, payload_path = _backup_paths(backup_store_root, backup_id)
    payload = bytearray(payload_path.read_bytes())
    payload[7] = (payload[7] + 11) % 255
    payload_path.write_bytes(bytes(payload))

    async with sqlite_session_factory() as session:
        service = BackupService(session)
        verification = await service.verify_backup(backup_id)
        assert verification.status == "corrupted"

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "blocked"


@pytest.mark.asyncio
async def test_sqlite_restore_blocks_after_key_rotation_or_loss(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "y" * 32)

    async with sqlite_session_factory() as session:
        service = BackupService(session)
        verification = await service.verify_backup(backup_id)
        assert verification.status == "corrupted"

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "blocked"


@pytest.mark.asyncio
async def test_sqlite_restore_rejects_corrupted_manifest(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    manifest_path, _ = _backup_paths(backup_store_root, backup_id)
    manifest_path.write_text("{not-json", encoding="utf-8")

    async with sqlite_session_factory() as session:
        with pytest.raises(ValueError, match="manifest is corrupted"):
            await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )


@pytest.mark.asyncio
async def test_sqlite_restore_rolls_back_when_promotion_fails_midway(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        ids = await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    async with sqlite_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)
        mutated_state = await collect_recovery_state(session, backup_repo_root, ids)

    original_write_text = Path.write_text
    failed = False

    def patched_write_text(path: Path, content: str, *args, **kwargs):
        nonlocal failed
        if not failed and path == backup_repo_root / "config" / "app.yaml":
            failed = True
            raise RuntimeError("simulated config promotion failure")
        return original_write_text(path, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", patched_write_text)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "failed"
        assert result.details["rollback_status"] == "success"
        assert result.details["pre_restore_backup_id"] is not None

    monkeypatch.undo()

    async with sqlite_session_factory() as session:
        recovered_state = await collect_recovery_state(session, backup_repo_root, ids)
    assert recovered_state == mutated_state


@pytest.mark.asyncio
async def test_sqlite_restore_blocks_concurrent_restore_attempts(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    entered = asyncio.Event()
    release = asyncio.Event()
    original_restore = SQLiteBackupProvider.restore_database
    call_count = 0

    async def blocked_restore(self, src_file: Path):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            entered.set()
            await release.wait()
        return await original_restore(self, src_file)

    monkeypatch.setattr(SQLiteBackupProvider, "restore_database", blocked_restore)

    async with sqlite_session_factory() as session_one:
        task = asyncio.create_task(
            RestoreStagingService(session_one).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )
        )
        await entered.wait()

        async with sqlite_session_factory() as session_two:
            with pytest.raises(HTTPException) as exc:
                await RestoreStagingService(session_two).restore_with_staging(
                    backup_id, BackupRestoreRequest(dry_run=False)
                )
            assert exc.value.status_code == 423

        release.set()
        result = await task
        assert result.status == "restored"


@pytest.mark.asyncio
async def test_sqlite_restore_rejects_path_traversal_in_backup_payload(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        await seed_recovery_state(session, backup_repo_root)
        service = BackupService(session)
        backup_id = (await service.create_backup(BackupCreateRequest(scope="full"))).backup_id
        _rewrite_backup_for_path_traversal(service, backup_store_root, backup_id)

    async with sqlite_session_factory() as session:
        with pytest.raises(ValueError, match="Directory traversal sequence"):
            await RestoreStagingService(session).restore_with_staging(
                backup_id, BackupRestoreRequest(dry_run=False)
            )


@pytest.mark.asyncio
@pytest.mark.backup_dr
async def test_sqlite_large_backup_round_trip(
    sqlite_session_factory,
    sqlite_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(sqlite_backup_db_url, backup_store_root)

    async with sqlite_session_factory() as session:
        ids = await seed_recovery_state(
            session, backup_repo_root, extra_agents=180, long_text_size=8192
        )
        expected = await collect_recovery_state(session, backup_repo_root, ids)
        backup_id = (
            await BackupService(session).create_backup(BackupCreateRequest(scope="full"))
        ).backup_id

    _, payload_path = _backup_paths(backup_store_root, backup_id)
    assert payload_path.stat().st_size > 300_000

    async with sqlite_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)

    async with sqlite_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert result.status == "restored"

    async with sqlite_session_factory() as session:
        actual = await collect_recovery_state(session, backup_repo_root, ids)
    assert actual == expected
