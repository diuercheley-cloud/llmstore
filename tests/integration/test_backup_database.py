import uuid
import pytest
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.backup.backup_service import BackupService
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.models.agents.agents import AgentDefinition

@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)

@pytest.mark.asyncio
async def test_full_database_backup_and_restore(isolated_db_url, tmp_path, monkeypatch):
    # Set up config directories and monkeypatch env
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
            name="Original Agent Name",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active"
        )
        session.add(agent)
        await session.commit()

    # 2. Create the full database backup
    async with session_local() as session:
        service = BackupService(session)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req)
        
        # Verify manifest metadata
        assert manifest.scope == "full"
        assert manifest.metadata["database_engine"] == "sqlite"
        assert "db.dump" in [c.file_name for c in manifest.components]
        assert manifest.metadata["alembic_head"] is not None
        assert manifest.metadata["dump_format"] == "sqlite-binary"
        backup_id = manifest.backup_id

    # 3. Mutate the database (simulate data corruption/loss)
    async with session_local() as session:
        result = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = result.scalar_one()
        db_agent.name = "Mutated Agent Name"
        await session.commit()

    # 4. Perform full database restore
    async with session_local() as session:
        service = BackupService(session)
        restore_result = await service.restore_backup(backup_id)
        assert restore_result.status == "restored"

    # 5. Verify the original database rows are successfully restored
    async with session_local() as session:
        result = await session.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        db_agent = result.scalar_one_or_none()
        assert db_agent is not None
        assert db_agent.name == "Original Agent Name"

    await engine.dispose()
