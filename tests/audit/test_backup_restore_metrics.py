import uuid
import pytest
import pytest_asyncio
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from prometheus_client import REGISTRY

import app.db.session
from app.db.base import Base
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition
from app.services.backup.backup_service import BackupService
from app.services.backup.restore_staging_service import RestoreStagingService
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.core.metrics import (
    BACKUP_LAST_SUCCESS_TIMESTAMP,
    BACKUP_AGE_SECONDS,
    BACKUP_FAILURE_TOTAL,
    RESTORE_FAILURE_TOTAL,
    RESTORE_DURATION_SECONDS,
    BACKUP_DURATION_SECONDS,
    BACKUP_SIZE_BYTES,
    ESTIMATED_RPO_SECONDS,
    MEASURED_RTO_SECONDS
)

TEST_DB_FILE = Path("/tmp/test-backup-restore-metrics.db")

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
async def test_backup_restore_operational_metrics(test_db, tmp_path, monkeypatch):
    session_factory = test_db
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "repo" / "VERSION").write_text("1.0.0", encoding="utf-8")
    
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    # Get baseline counter values
    initial_backup_failures = REGISTRY.get_sample_value("backup_failure_total") or 0.0
    initial_restore_failures = REGISTRY.get_sample_value("restore_failure_total") or 0.0

    # 1. Successful backup
    async with session_factory() as db:
        service = BackupService(db)
        req = BackupCreateRequest(scope="full")
        manifest = await service.create_backup(req, actor="creator")
        backup_id = manifest.backup_id

    # Force dynamic metrics update (simulating what the /metrics endpoint does)
    from app.core.metrics import update_dynamic_backup_metrics
    update_dynamic_backup_metrics()

    # Assert success metrics
    last_success = REGISTRY.get_sample_value("backup_last_success_timestamp")
    assert last_success is not None
    assert last_success > 0.0

    age = REGISTRY.get_sample_value("backup_age_seconds")
    assert age is not None
    assert age >= 0.0

    size = REGISTRY.get_sample_value("backup_size_bytes")
    assert size is not None
    assert size > 0.0

    rpo = REGISTRY.get_sample_value("estimated_rpo_seconds")
    assert rpo is not None
    assert rpo >= 0.0

    # Check duration histogram has sample
    duration_count = REGISTRY.get_sample_value("backup_duration_seconds_count")
    assert duration_count is not None
    assert duration_count > 0.0

    # 2. Simulate Backup Failure
    # We can patch a method to raise an error
    with patch.object(BackupService, "_build_archive", side_effect=ValueError("Simulated archive error")):
        async with session_factory() as db:
            service = BackupService(db)
            with pytest.raises(ValueError):
                await service.create_backup(req, actor="creator")

    assert REGISTRY.get_sample_value("backup_failure_total") == initial_backup_failures + 1.0

    # 3. Successful Restore
    async with session_factory() as db:
        staging_svc = RestoreStagingService(db)
        res = await staging_svc.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False), actor="restore-operator")
        assert res.status == "restored"

    # Assert restore metrics
    rto = REGISTRY.get_sample_value("measured_rto_seconds")
    assert rto is not None
    assert rto >= 0.0

    restore_dur_count = REGISTRY.get_sample_value("restore_duration_seconds_count")
    assert restore_dur_count is not None
    assert restore_dur_count > 0.0

    # 4. Simulate Restore Failure
    with patch.object(RestoreStagingService, "_restore_with_staging_impl", side_effect=ValueError("Simulated restore error")):
        async with session_factory() as db:
            staging_svc = RestoreStagingService(db)
            with pytest.raises(ValueError):
                await staging_svc.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=False), actor="restore-operator")

    assert REGISTRY.get_sample_value("restore_failure_total") == initial_restore_failures + 1.0
