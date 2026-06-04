# Owner: agent-platform
import hashlib
import json
import uuid
from datetime import timedelta
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.core.time import utc_now
from app.db.base import Base
from app.models.agent_execution import AgentExecutionJob
from app.models.agents import AgentDefinition, AgentRun, AgentRunReceipt
from app.services.agents.deterministic_state_graph import (
    AgentRunState,
    DeterministicStateGraph,
)
from app.services.agents.replay_runner import ReplayMismatchError, ReplayRunner
from app.services.agents.runtime_reconstruction import (
    RuntimeReconstructionService,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = Path("/tmp/test-runtime-determinism.db")


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
        except:
            pass


@pytest.mark.asyncio
async def test_state_transitions_validation():
    # Verify state transitions validation logic
    dsg = DeterministicStateGraph("v1.0")
    
    # Valid transition
    assert dsg.validate_transition(AgentRunState, AgentRunState.QUEUED, AgentRunState.RUNNING) is True
    assert dsg.validate_transition(AgentRunState, AgentRunState.RUNNING, AgentRunState.COMPLETED) is True
    
    # Invalid transition (e.g. from COMPLETED to RUNNING is forbidden in v1.0)
    assert dsg.validate_transition(AgentRunState, AgentRunState.COMPLETED, AgentRunState.RUNNING) is False


@pytest.mark.asyncio
async def test_crash_during_tool_call(test_db):
    async with test_db() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(), name="Test Agent", tenant_id="t1", status="active",
            instructions="Test", model_id="gpt-3.5-turbo", owner="admin", version="1.0.0"
        )
        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running",
            input_text="Run tool", total_steps=0, total_tokens=0, estimated_cost_brl=0.0
        )
        db.add(agent)
        db.add(run)
        await db.commit()

        # Simulate receipt generated for tool_execution before crash
        receipt_data = {
            "type": "tool_execution",
            "input_hash": hashlib.sha256(b"{}").hexdigest(),
            "output_hash": hashlib.sha256(b"result").hexdigest(),
            "metadata": {"tool_name": "calc", "input": {}},
            "success": True,
            "timestamp": utc_now().isoformat()
        }
        receipt = AgentRunReceipt(
            run_id=run.id,
            step_number=1,
            receipt_data=receipt_data,
            signature="sig_tool_call_mock",
            created_at=utc_now()
        )
        db.add(receipt)
        
        # Simulate active execution job that gets orphaned
        job = AgentExecutionJob(
            id=uuid.uuid4(),
            agent_run_id=run.id,
            agent_id=run.agent_id,
            tenant_id="t1",
            queue_status="running",
            created_at=utc_now() - timedelta(minutes=10) # 10 minutes ago -> expired lease
        )
        db.add(job)
        await db.commit()

        # Run recovery/reconstruction
        reconstruction = RuntimeReconstructionService(db)
        result = await reconstruction.reconstruct_run_state(run.id)

        assert result["status"] == "queued"  # Run reset to queued after orphan recovery
        assert result["lease_recovered"] is True
        assert result["total_steps"] == 1


@pytest.mark.asyncio
async def test_crash_during_memory_write(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        receipt_data = {
            "type": "memory_mutation",
            "input_hash": hashlib.sha256(b"write").hexdigest(),
            "output_hash": hashlib.sha256(b"written").hexdigest(),
            "metadata": {"key": "user_name", "value": "Alice"},
            "success": True,
            "timestamp": utc_now().isoformat()
        }
        receipt = AgentRunReceipt(
            run_id=run.id, step_number=1, receipt_data=receipt_data, signature="sig_mem_mock"
        )
        db.add(receipt)
        await db.commit()

        reconstruction = RuntimeReconstructionService(db)
        result = await reconstruction.reconstruct_run_state(run.id)
        
        assert result["total_steps"] == 1
        assert len(result["reconstructed_steps"]) == 1


@pytest.mark.asyncio
async def test_crash_during_approval_wait(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        # Run is waiting for approval
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="waiting_approval", input_text="X", total_steps=1, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        # Approval wait should preserve the status after reconstruction
        reconstruction = RuntimeReconstructionService(db)
        result = await reconstruction.reconstruct_run_state(run.id)

        assert result["status"] == "waiting_approval"
        assert result["lease_recovered"] is False


@pytest.mark.asyncio
async def test_worker_death_during_workflow_wakeup(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        # Job with expired lease
        job = AgentExecutionJob(
            id=uuid.uuid4(),
            agent_run_id=run.id,
            agent_id=run.agent_id,
            tenant_id="t1",
            queue_status="running",
            created_at=utc_now() - timedelta(minutes=15)
        )
        db.add(job)
        await db.commit()

        reconstruction = RuntimeReconstructionService(db)
        result = await reconstruction.reconstruct_run_state(run.id)

        assert result["status"] == "queued"
        assert result["lease_recovered"] is True

        # Re-fetch job to check status updated to failed
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job.id)
        res = await db.execute(stmt)
        updated_job = res.scalar_one()
        assert updated_job.queue_status == "failed"


@pytest.mark.asyncio
async def test_replay_consistency_and_mismatch(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="completed", input_text="X", total_steps=1, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        # Step 1: correct tool execution receipt
        tool_input = {"a": 1}
        input_hash = hashlib.sha256(json.dumps(tool_input, sort_keys=True).encode("utf-8")).hexdigest()
        receipt_data = {
            "type": "tool_execution",
            "input_hash": input_hash,
            "output_hash": hashlib.sha256(b"out").hexdigest(),
            "metadata": {"tool_name": "calc", "input": tool_input},
            "success": True,
            "timestamp": utc_now().isoformat()
        }
        receipt = AgentRunReceipt(
            run_id=run.id, step_number=1, receipt_data=receipt_data, signature="sig_ok"
        )
        db.add(receipt)
        await db.commit()

        # Replay runs successfully
        runner = ReplayRunner(db, run.id)
        report = await runner.run_replay()
        assert report["status"] == "verified"
        assert report["replay_hash"] is not None

        # Alter the parameters to simulate drift / mismatch
        receipt.receipt_data["metadata"]["input"] = {"a": 2} # altered input
        db.add(receipt)
        await db.commit()

        # Replay should now fail
        with pytest.raises(ReplayMismatchError):
            await runner.run_replay()


@pytest.mark.asyncio
async def test_duplicate_signal_handling(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        # First signal receipt
        signal_payload = {"signal": "pause"}
        input_hash = hashlib.sha256(json.dumps(signal_payload, sort_keys=True).encode("utf-8")).hexdigest()
        receipt_data = {
            "type": "workflow_signal",
            "input_hash": input_hash,
            "output_hash": hashlib.sha256(b"done").hexdigest(),
            "metadata": {"signal_name": "user_pause", "payload": signal_payload},
            "success": True,
            "timestamp": utc_now().isoformat()
        }
        receipt = AgentRunReceipt(
            run_id=run.id, step_number=1, receipt_data=receipt_data, signature="sig_sig_1"
        )
        db.add(receipt)
        await db.commit()

        # Verify replay is consistent
        runner = ReplayRunner(db, run.id)
        report = await runner.run_replay()
        assert report["status"] == "verified"
