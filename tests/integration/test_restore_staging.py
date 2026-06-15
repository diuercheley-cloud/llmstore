import uuid
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup.backup_service import BackupService
from app.services.backup.restore_staging_service import RestoreStagingService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)


@pytest.mark.asyncio
async def test_staging_restore_validation_failures_and_dry_run(
    isolated_db_url, tmp_path, monkeypatch
):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")

    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # Connect to isolated database
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create the tables
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Seed some database rows
    agent_id = uuid.uuid4()
    async with session_local() as session:
        agent = AgentDefinition(
            id=agent_id,
            name="Original Production Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active",
        )
        session.add(agent)
        await session.commit()

    # 2. Create a backup
    async with session_local() as session:
        service = BackupService(session)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req)
        backup_id = manifest.backup_id

    # 3. Test: Manifest/Signature corruption does not alter production
    # Tamper with the encrypted archive payload to trigger verification failure
    payload_path = (
        Path(settings.disaster_recovery_backup_dir) / "system" / backup_id / manifest.payload_file
    )
    original_payload = payload_path.read_bytes()
    # Write corrupt bytes
    payload_path.write_bytes(b"corrupted_bytes_that_fail_decryption_or_hmac")

    async with session_local() as session:
        staging_svc = RestoreStagingService(session)
        res = await staging_svc.restore_with_staging(backup_id)
        assert res.status == "blocked"
        assert res.details["validation_report"]["manifest_valid"] is False

    # Verify production data is unaffected
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        assert db_agent.name == "Original Production Agent"

    # Restore the original valid payload
    payload_path.write_bytes(original_payload)

    # 4. Test: Dry-run restore does not alter production data
    # Mutate production database first so we can verify if dry-run reverts it
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        db_agent.name = "Mutated Production Agent"
        await session.commit()

    async with session_local() as session:
        staging_svc = RestoreStagingService(session)
        dry_run_res = await staging_svc.restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=True)
        )
        assert dry_run_res.status == "dry_run_complete"
        assert dry_run_res.details["side_effects_prevented"] is True
        assert dry_run_res.details["validation_report"]["database_valid"] is True

    # Verify production data remains mutated (dry-run did NOT restore/promote it!)
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        assert db_agent.name == "Mutated Production Agent"

    # 5. Test: Real restore promotion works
    async with session_local() as session:
        staging_svc = RestoreStagingService(session)
        restore_res = await staging_svc.restore_with_staging(
            backup_id, BackupRestoreRequest(dry_run=False)
        )
        assert restore_res.status == "restored"

    # Verify production data is now restored to original
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        assert db_agent.name == "Original Production Agent"

    await engine.dispose()


@pytest.mark.asyncio
async def test_restore_failure_after_database_rollback(isolated_db_url, tmp_path, monkeypatch):
    # Setup directories
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "repo" / "config" / "settings.json"
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")

    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # Connect to isolated database
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create the tables
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Set original production state
    agent_id = uuid.uuid4()
    async with session_local() as session:
        agent = AgentDefinition(
            id=agent_id,
            name="Original Production Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active",
        )
        session.add(agent)
        await session.commit()
    config_file.write_text("original_config", encoding="utf-8")

    # 2. Create the backup that we want to restore later
    async with session_local() as session:
        service = BackupService(session)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req)
        backup_to_restore_id = manifest.backup_id

    # 3. Change active state to new state (before restore)
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        db_agent.name = "Modified Production Agent"
        await session.commit()
    config_file.write_text("modified_config", encoding="utf-8")

    # 4. Simulate failure right after database restore, before config restore
    should_fail = True
    original_write_text = Path.write_text

    def patched_write_text(self_path, content, *args, **kwargs):
        nonlocal should_fail
        if should_fail and "repo/config" in str(self_path):
            should_fail = False
            raise RuntimeError("Simulated config promotion failure")
        return original_write_text(self_path, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", patched_write_text)

    async with session_local() as session:
        staging_svc = RestoreStagingService(session)
        res = await staging_svc.restore_with_staging(
            backup_to_restore_id, BackupRestoreRequest(dry_run=False)
        )

        # Confirm rollback was triggered and succeeded
        assert res.status == "failed"
        assert res.details["rollback_status"] == "success"
        assert res.details["pre_restore_backup_id"] is not None

    # Verify production agent is rolled back to "Modified Production Agent"
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        assert db_agent.name == "Modified Production Agent"

    # Verify config file is rolled back to "modified_config"
    monkeypatch.undo()
    assert config_file.read_text(encoding="utf-8") == "modified_config"

    await engine.dispose()


@pytest.mark.asyncio
async def test_restore_failure_after_configs_rollback(isolated_db_url, tmp_path, monkeypatch):
    # Setup directories
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "repo" / "config" / "settings.json"
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")

    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # Connect to isolated database
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create the tables
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Set original production state
    agent_id = uuid.uuid4()
    async with session_local() as session:
        agent = AgentDefinition(
            id=agent_id,
            name="Original Production Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active",
        )
        session.add(agent)
        await session.commit()
    config_file.write_text("original_config", encoding="utf-8")

    # 2. Create the backup that we want to restore later
    async with session_local() as session:
        service = BackupService(session)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req)
        backup_to_restore_id = manifest.backup_id

    # 3. Change active state to new state (before restore)
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        db_agent.name = "Modified Production Agent"
        await session.commit()
    config_file.write_text("modified_config", encoding="utf-8")

    # 4. Simulate failure right after configs restore, before feature flags
    should_fail = True

    def mock_restore_ff(*args, **kwargs):
        nonlocal should_fail
        if should_fail:
            should_fail = False
            raise RuntimeError("Simulated failure after configs restore")
        return None

    monkeypatch.setattr(BackupService, "_restore_feature_flags", mock_restore_ff)

    async with session_local() as session:
        staging_svc = RestoreStagingService(session)
        res = await staging_svc.restore_with_staging(
            backup_to_restore_id, BackupRestoreRequest(dry_run=False)
        )

        # Confirm rollback was triggered and succeeded
        assert res.status == "failed"
        assert res.details["rollback_status"] == "success"
        assert res.details["pre_restore_backup_id"] is not None

    # Verify production agent is rolled back to "Modified Production Agent"
    async with session_local() as session:
        res = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        assert db_agent.name == "Modified Production Agent"

    # Verify config file is rolled back to "modified_config"
    assert config_file.read_text(encoding="utf-8") == "modified_config"

    await engine.dispose()
