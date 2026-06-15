from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import get_settings
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup.backup_service import BackupService
from app.services.backup.restore_staging_service import RestoreStagingService

from tests.backup.fixtures import collect_recovery_state, mutate_recovery_state, seed_recovery_state

pytestmark = [pytest.mark.integration, pytest.mark.backup_dr]


def _configure_settings(database_url: str, backup_store_root: Path) -> None:
    settings = get_settings()
    settings.database_url = database_url
    settings.disaster_recovery_backup_dir = str(backup_store_root)
    settings.backup_restore_enabled = True
    settings.deployment_mode = "local"


@pytest.mark.asyncio
async def test_postgres_full_restore_recovers_all_required_domains(
    postgres_session_factory,
    postgres_backup_db_url: str,
    backup_repo_root: Path,
    backup_store_root: Path,
):
    _configure_settings(postgres_backup_db_url, backup_store_root)

    async with postgres_session_factory() as session:
        ids = await seed_recovery_state(session, backup_repo_root)
        expected = await collect_recovery_state(session, backup_repo_root, ids)
        manifest = await BackupService(session).create_backup(
            BackupCreateRequest(scope="full"), actor="postgres-dr"
        )
        assert manifest.scope == "full"
        assert manifest.metadata["database_engine"] == "postgresql"
        backup_id = manifest.backup_id

    async with postgres_session_factory() as session:
        await mutate_recovery_state(session, backup_repo_root, ids)

    async with postgres_session_factory() as session:
        result = await RestoreStagingService(session).restore_with_staging(
            backup_id,
            BackupRestoreRequest(dry_run=False),
            actor="postgres-dr",
        )
        assert result.status == "restored"

    async with postgres_session_factory() as session:
        actual = await collect_recovery_state(session, backup_repo_root, ids)
    assert actual == expected
