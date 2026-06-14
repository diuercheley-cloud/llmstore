import uuid
import pytest
import pytest_asyncio
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.session
from app.db.base import Base
from app.core.config import get_settings
from app.models.agents.immutable_audit import ImmutableAuditLog
from app.models.agents.agents import AgentDefinition
from app.services.backup.backup_service import BackupService
from app.services.backup.restore_staging_service import RestoreStagingService
from app.services.security.immutable_audit import ImmutableAuditStore
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest

TEST_DB_FILE = Path("/tmp/test-backup-restore-audit.db")

@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)

@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield session_factory
    
    await engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

@pytest.mark.asyncio
async def test_backup_audit_logging_and_tamper_detection(test_db, tmp_path, monkeypatch):
    session_factory = test_db
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "repo" / "config" / "settings.json"
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")
    config_file.write_text("original_config", encoding="utf-8")

    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # 1. Seed some database rows
    agent_id = uuid.uuid4()
    async with session_factory() as db:
        agent = AgentDefinition(
            id=agent_id,
            name="Original Production Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active"
        )
        db.add(agent)
        await db.commit()

    # 2. Create backup and verify backup_created and backup_verified logs are written
    async with session_factory() as db:
        service = BackupService(db)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req, actor="admin-operator")
        backup_id = manifest.backup_id

    async with session_factory() as db:
        # Check audit logs in db
        stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        
        # We expect backup_verified (during create_backup verification check) and backup_created
        actions = [log.action for log in logs]
        assert "backup_created" in actions
        assert "backup_verified" in actions
        
        # Check values logged in payload
        created_log = next(log for log in logs if log.action == "backup_created")
        payload = json.loads(created_log.payload)
        assert payload["actor"] == "admin-operator"
        assert payload["backup_id"] == backup_id
        assert payload["result"] == "success"

    # 3. Fetch/download backup and verify backup_downloaded log
    async with session_factory() as db:
        service = BackupService(db)
        await service.get_backup(backup_id, actor="download-user")

    async with session_factory() as db:
        stmt = select(ImmutableAuditLog).where(ImmutableAuditLog.action == "backup_downloaded")
        res = await db.execute(stmt)
        download_log = res.scalar_one()
        payload = json.loads(download_log.payload)
        assert payload["actor"] == "download-user"
        assert payload["backup_id"] == backup_id
        assert payload["target"] == "download"

    # 4. Tamper detection verification
    async with session_factory() as db:
        is_valid, failed_id, reason = await ImmutableAuditStore.verify_chain(db)
        assert is_valid is True

        # Tamper with an older log entry in the database
        stmt = select(ImmutableAuditLog).where(ImmutableAuditLog.action == "backup_created")
        res = await db.execute(stmt)
        tamp_log = res.scalar_one()
        tamp_log.payload = json.dumps({"tampered": True})
        db.add(tamp_log)
        await db.commit()

        # Chain verification must now fail
        is_valid, failed_id, reason = await ImmutableAuditStore.verify_chain(db)
        assert is_valid is False
        assert failed_id == tamp_log.id
        assert "Hash mismatch" in reason


@pytest.mark.asyncio
async def test_restore_and_rollback_audit_logging(test_db, tmp_path, monkeypatch):
    session_factory = test_db
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    config_file = tmp_path / "repo" / "config" / "settings.json"
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")
    config_file.write_text("original_config", encoding="utf-8")

    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # 1. Seed database
    agent_id = uuid.uuid4()
    async with session_factory() as db:
        agent = AgentDefinition(
            id=agent_id,
            name="Original Production Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active"
        )
        db.add(agent)
        await db.commit()

    # 2. Create the backup to restore later
    async with session_factory() as db:
        service = BackupService(db)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req, actor="creator")
        backup_id = manifest.backup_id

    # 3. Mutate active state
    async with session_factory() as db:
        res = await db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = res.scalar_one()
        db_agent.name = "Modified Production Agent"
        await db.commit()
    config_file.write_text("modified_config", encoding="utf-8")

    # 4. Perform restore and verify successful restore logs
    # We expect: restore_requested, restore_approved, restore_started, restore_completed
    async with session_factory() as db:
        staging_svc = RestoreStagingService(db)
        res = await staging_svc.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False), actor="restore-operator")
        assert res.status == "restored"

    async with session_factory() as db:
        stmt = select(ImmutableAuditLog).where(ImmutableAuditLog.action.like("restore_%")).order_by(ImmutableAuditLog.id.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        actions = [log.action for log in logs]
        
        assert "restore_requested" in actions
        assert "restore_approved" in actions
        assert "restore_started" in actions
        assert "restore_completed" in actions

        # Check actor in restore logs
        completed_log = next(log for log in logs if log.action == "restore_completed")
        payload = json.loads(completed_log.payload)
        assert payload["actor"] == "restore-operator"
        assert payload["result"] == "success"

    # 5. Simulate failure during promotion to trigger rollback audit logs
    # We expect: restore_failed, rollback_started, rollback_completed
    restore_state_file = tmp_path / "backup-store" / "restore-state.json"
    if restore_state_file.exists():
        restore_state_file.unlink()
    restore_state_file_alt = tmp_path / "backup-store" / "system" / "restore-state.json"
    if restore_state_file_alt.exists():
        restore_state_file_alt.unlink()

    should_fail = True
    original_write_text = Path.write_text
    def patched_write_text(self_path, content, *args, **kwargs):
        nonlocal should_fail
        if should_fail and ("repo/config" in str(self_path) or "repo/VERSION" in str(self_path)):
            should_fail = False
            raise RuntimeError("Simulated config promotion failure")
        return original_write_text(self_path, content, *args, **kwargs)
    
    monkeypatch.setattr(Path, "write_text", patched_write_text)

    async with session_factory() as db:
        staging_svc = RestoreStagingService(db)
        res = await staging_svc.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False), actor="rollback-operator")
        assert res.status == "failed"

    async with session_factory() as db:
        stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        actions = [log.action for log in logs]

        assert "restore_failed" in actions
        assert "rollback_started" in actions
        assert "rollback_completed" in actions

        completed_rollback = next(log for log in logs if log.action == "rollback_completed")
        payload = json.loads(completed_rollback.payload)
        assert payload["actor"] == "rollback-operator"
        assert payload["result"] == "success"
