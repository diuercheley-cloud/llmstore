import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.agents.agent_execution import (
    AgentExecutionJob,
    AgentExecutionLease,
    AgentWorkerHeartbeat,
)
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.agent_worker import AgentWorkerService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-worker-operability.db")


@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_file = Path(f"/tmp/test-worker-{uuid.uuid4()}.db")
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Patch the global session and engine
    import app.services.agents.agent_worker

    orig_engine = app.db.session.engine
    orig_session = app.db.session.SessionLocal
    orig_worker_session = app.services.agents.agent_worker.SessionLocal

    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory
    app.services.agents.agent_worker.SessionLocal = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()
    if db_file.exists():
        try:
            db_file.unlink()
        except:
            pass

    app.db.session.engine = orig_engine
    app.db.session.SessionLocal = orig_session
    app.services.agents.agent_worker.SessionLocal = orig_worker_session


@pytest_asyncio.fixture(autouse=True)
async def setup_settings():
    from app.core.config import get_settings

    settings = get_settings()
    orig_plane = settings.agent_execution_plane_enabled
    orig_worker = settings.agent_worker_enabled
    settings.agent_execution_plane_enabled = True
    settings.agent_worker_enabled = True
    yield
    settings.agent_execution_plane_enabled = orig_plane
    settings.agent_worker_enabled = orig_worker


@pytest.mark.asyncio
async def test_worker_heartbeat_and_active_metrics(test_db):
    worker = AgentWorkerService(worker_id="test-worker")

    async with test_db() as db:
        await worker.register_heartbeat(db)

        stmt = select(AgentWorkerHeartbeat).where(AgentWorkerHeartbeat.worker_id == "test-worker")
        res = await db.execute(stmt)
        hb = res.scalar_one()
        assert hb.status == "active"


@pytest.mark.asyncio
async def test_worker_drain_prevents_pickup(test_db):
    worker = AgentWorkerService(worker_id="draining-worker")
    worker.drain()  # Enter drain mode

    async with test_db() as db:
        # Create a job
        job = AgentExecutionJob(
            id=uuid.uuid4(),
            agent_run_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            tenant_id="t1",
            status="queued",
            scheduled_at=datetime.now(UTC),
        )
        db.add(job)
        await db.commit()

    # Try to run once
    executed = await worker.run_once()
    assert executed is False  # Should return False immediately because of drain


@pytest.mark.asyncio
async def test_orphan_lease_recovery(test_db):
    worker = AgentWorkerService(worker_id="recovery-worker")

    async with test_db() as db:
        job_id = uuid.uuid4()
        job = AgentExecutionJob(
            id=job_id,
            agent_run_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            tenant_id="t1",
            status="running",
            scheduled_at=datetime.now(UTC),
        )
        # Create an expired lease
        lease = AgentExecutionLease(
            job_id=job_id,
            worker_id="dead-worker",
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        db.add(job)
        db.add(lease)
        await db.commit()

        # Run recovery
        recovered = await worker.recover_orphans(db)
        assert recovered == 1

        # Verify job is back to queued
        await db.refresh(job)
        assert job.status == "queued"


@pytest.mark.asyncio
async def test_job_reaches_dlq_after_max_attempts(test_db):
    worker = AgentWorkerService(worker_id="failing-worker")

    async with test_db() as db:
        job_id = uuid.uuid4()
        run_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        agent = AgentDefinition(
            id=agent_id,
            name="A",
            tenant_id="t1",
            status="active",
            instructions="I",
            model_id="m",
            owner="o",
            version="1",
        )
        run = AgentRun(
            id=run_id,
            agent_id=agent_id,
            tenant_id="t1",
            status="running",
            total_steps=0,
            total_tokens=0,
            estimated_cost_brl=0.0,
        )

        job = AgentExecutionJob(
            id=job_id,
            agent_run_id=run_id,
            agent_id=agent_id,
            tenant_id="t1",
            status="running",
            attempts=2,
            max_attempts=3,
            initial_delay_seconds=1,
            backoff_factor=2,
        )
        db.add(agent)
        db.add(run)
        db.add(job)
        await db.commit()

        # Simulate a fatal failure
        await worker._handle_job_failure(job_id, "Fatal Error")

        # Verify job is in dead_letter status
        await db.refresh(job)
        assert job.status == "dead_letter"
