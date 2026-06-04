import os
import uuid
from pathlib import Path

# Force SQLite for tests before any app imports
TEST_TMP = Path("/tmp/llm-inference-stack-control-plane-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "workflow-test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agent_workflows import (
    AgentWorkflow,
    AgentWorkflowEvent,
    AgentWorkflowTimer,
)
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from app.services.agents.workflows.workflow_state_machine import WorkflowStatus
from sqlalchemy import select


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
        assert run.state_data["resume_to_state"] == "end"
        
        now = utc_now()
        next_exec = run.next_execution_at
        if next_exec.tzinfo is None and now.tzinfo is not None:
            next_exec = next_exec.replace(tzinfo=now.tzinfo)
        
        assert next_exec > now
        timers = (
            await db_session.execute(select(AgentWorkflowTimer).where(AgentWorkflowTimer.run_id == run.id))
        ).scalars().all()
        assert len(timers) == 1
        assert timers[0].status == "pending"

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

@pytest.mark.asyncio
async def test_workflow_handoff_and_signal_resume_end_to_end(db_session, workflow):
    with patch.dict(os.environ, {"AGENT_STATEFUL_WORKFLOWS_ENABLED": "true"}):
        get_settings.cache_clear()
        engine_service = WorkflowEngine(db_session)
        run = await engine_service.create_run(
            workflow.id,
            "default",
            {
                "state_machine": {
                    "start": {"action": "handoff", "next_state": "collect"},
                    "collect": {
                        "action": "wait_signal",
                        "signal": "external_ready",
                        "resume_to_state": "finalize",
                    },
                    "finalize": {"action": "complete", "result": "workflow finalized"},
                }
            },
        )

        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.current_state == "collect"
        assert run.status == WorkflowStatus.RUNNING.value

        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.status == WorkflowStatus.WAITING_SIGNAL.value
        assert run.state_data["expected_signal"] == "external_ready"
        assert run.state_data["resume_to_state"] == "finalize"

        await engine_service.signal_run(run.id, "external_ready", {"approved": True})
        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.status == WorkflowStatus.COMPLETED.value
        assert run.current_state == "finalize"
        assert run.state_data["result"] == "workflow finalized"
        assert run.context["last_signal"]["name"] == "external_ready"

        events = (
            await db_session.execute(select(AgentWorkflowEvent).where(AgentWorkflowEvent.run_id == run.id))
        ).scalars().all()
        event_types = {event.event_type for event in events}
        assert "status_transition" in event_types
        assert "state_handoff" in event_types

@pytest.mark.asyncio
async def test_workflow_version_migration_and_compensation(db_session, workflow):
    with patch.dict(os.environ, {"AGENT_STATEFUL_WORKFLOWS_ENABLED": "true"}):
        get_settings.cache_clear()
        engine_service = WorkflowEngine(db_session)
        run = await engine_service.create_run(
            workflow.id,
            "default",
            {
                "workflow_version": "1.0.0",
                "target_workflow_version": "2.0.0",
                "state_machine": {
                    "start_v2": {
                        "action": "fail",
                        "reason": "forced failure",
                        "compensation": {
                            "action": "set_context",
                            "updates": {"compensated": True},
                        },
                    }
                },
                "state_migrations": {
                    "1.0.0->2.0.0": {
                        "state_mapping": {"start": "start_v2"},
                        "context_updates": {"migration_flag": "applied"},
                    }
                },
            },
        )

        await engine_service.execute_step(run.id)
        await db_session.refresh(run)
        assert run.status == WorkflowStatus.RETRY_SCHEDULED.value
        assert run.current_state == "start_v2"
        assert run.context["workflow_version"] == "2.0.0"
        assert run.context["migration_flag"] == "applied"
        assert run.context["compensated"] is True
        assert run.state_data["migration_applied"]["from_version"] == "1.0.0"
        assert run.state_data["compensation_log"][0]["action"] == "set_context"
