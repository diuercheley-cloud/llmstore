import os
import uuid
from pathlib import Path

# Force SQLite for tests before any app imports
TEST_TMP = Path("/tmp/llm-inference-stack-control-plane-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "workflow-test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from unittest.mock import patch, MagicMock

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.agent_workflows import AgentWorkflow, AgentWorkflowRun, AgentWorkflowTimer, AgentWorkflowSignal
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from app.services.agents.workflows.workflow_timers import WorkflowTimerManager
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from app.services.agents.workflows.workflow_state_machine import WorkflowStatus
from app.core.time import utc_now
from app.core.config import get_settings

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agent_workflows  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session

@pytest.fixture
async def workflow(db_session):
    workflow = AgentWorkflow(
        name="test-workflow",
        version="1.0.0",
        tenant_id="default"
    )
    db_session.add(workflow)
    await db_session.commit()
    return workflow

@pytest.mark.asyncio
async def test_workflow_sleeps_and_wakes_up(db_session, workflow):
    with patch.dict(os.environ, {"AGENT_STATEFUL_WORKFLOWS_ENABLED": "true"}):
        get_settings.cache_clear()
        engine_service = WorkflowEngine(db_session)
        
        # 1. Create run
        run = await engine_service.create_run(workflow.id, "default", {"sleep_seconds": 1})
        
        # 2. Execute start -> process
        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.current_state == "process"
        
        # 3. Execute process -> sleeping
        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.status == WorkflowStatus.SLEEPING.value
        
        now = utc_now()
        next_exec = run.next_execution_at
        if next_exec.tzinfo is None and now.tzinfo is not None:
            next_exec = next_exec.replace(tzinfo=now.tzinfo)
        
        assert next_exec > now

@pytest.mark.asyncio
async def test_signal_wakes_up_workflow(db_session, workflow):
    with patch.dict(os.environ, {"AGENT_STATEFUL_WORKFLOWS_ENABLED": "true"}):
        get_settings.cache_clear()
        engine_service = WorkflowEngine(db_session)
        signals = WorkflowSignalManager(db_session)
        
        # 1. Create run and put in waiting state
        run = await engine_service.create_run(workflow.id, "default", {})
        run.status = WorkflowStatus.WAITING_SIGNAL.value
        await db_session.commit()
        
        # 2. Send signal
        await signals.send_signal(run.id, "test_signal", {"data": "ok"})
        
        # 3. Verify workflow is ready
        await db_session.refresh(run)
        assert run.status == "running"

@pytest.mark.asyncio
async def test_lease_prevents_duplicate_execution(db_session, workflow):
    from app.services.agents.workflows.workflow_locks import WorkflowLockManager
    locks = WorkflowLockManager(db_session)
    
    lock_key = f"workflow_run:{uuid.uuid4()}"
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    
    # owner A acquires
    assert await locks.acquire_lock(lock_key, owner_a) is True
    
    # owner B cannot acquire
    assert await locks.acquire_lock(lock_key, owner_b) is False
    
    # owner A releases
    await locks.release_lock(lock_key, owner_a)
    
    # owner B can now acquire
    assert await locks.acquire_lock(lock_key, owner_b) is True

@pytest.mark.asyncio
async def test_workflow_cancellation(db_session, workflow):
    with patch.dict(os.environ, {"AGENT_STATEFUL_WORKFLOWS_ENABLED": "true"}):
        get_settings.cache_clear()
        engine_service = WorkflowEngine(db_session)
        run = await engine_service.create_run(workflow.id, "default", {})
        
        await engine_service.cancel_run(run.id)
        await db_session.refresh(run)
        assert run.status == WorkflowStatus.CANCELLED.value
