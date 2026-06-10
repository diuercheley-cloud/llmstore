import uuid
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.agents.agents import (
    AgentDefinition,
    AgentRun,
    AgentRunEvent,
    AgentRunReceipt,
)
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.agents.agent_llm_provider import GatewayAgentLLMProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-deterministic-executor.db")

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
        try: TEST_DB_FILE.unlink()
        except: pass

from app.core.config import get_settings


@pytest_asyncio.fixture(autouse=True)
async def setup_settings():
    settings = get_settings()
    orig_obs = settings.agent_observability_enabled
    orig_sandbox = settings.agent_tool_sandbox_enabled
    orig_exec = settings.agent_execution_enabled
    orig_tool_exec = settings.agent_tool_execution_enabled
    orig_executor_mock = settings.agent_executor_mock_mode
    
    settings.agent_observability_enabled = True
    settings.agent_tool_sandbox_enabled = False
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_executor_mock_mode = True
    
    yield
    
    settings.agent_observability_enabled = orig_obs
    settings.agent_tool_sandbox_enabled = orig_sandbox
    settings.agent_execution_enabled = orig_exec
    settings.agent_tool_execution_enabled = orig_tool_exec
    settings.agent_executor_mock_mode = orig_executor_mock

pytest_mark_asyncio = pytest.mark.asyncio

@pytest_mark_asyncio
async def test_run_complete_generates_ordered_events(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(), name="Test Agent", tenant_id="t1", status="active",
            instructions="Test instructions", model_id="gpt-3.5-turbo", owner="admin",
            version="1.0.0"
        )
        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="queued",
            input_text="Hello", total_steps=0, total_tokens=0, estimated_cost_brl=0.0
        )
        db.add(agent)
        db.add(run)
        await db.commit()

        # Mock LLM to return final response
        mock_llm = MockLLMProvider([{"type": "final", "output": "Goodbye", "usage": {"prompt_tokens": 10, "completion_tokens": 5}}])
        
        executor = AgentExecutor(db, run.id, llm_provider=mock_llm)
        
        # Step 1: orchestration + final response
        await executor.execute_step()
        
        # Verify events
        stmt = select(AgentRunEvent).where(AgentRunEvent.run_id == run.id).order_by(AgentRunEvent.created_at.asc())
        res = await db.execute(stmt)
        events = res.scalars().all()
        
        event_types = [e.event_type for e in events]
        assert "run_started" in event_types
        assert "step_started" in event_types
        assert "model_call_completed" in event_types
        assert "run_completed" in event_types

@pytest.mark.asyncio
async def test_tool_failure_generates_receipt(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        
        from app.models.agents.agents import AgentTool
        tool = AgentTool(
            id=uuid.uuid4(), name="bad_tool", description="D", 
            category="test", input_schema_json={}, output_schema_json={},
            enabled=True
        )
        db.add(tool)
        
        await db.commit()

        # Mock tool runner that fails
        async def failing_tool(name, inputs):
            raise ValueError("Tool exploded")

        settings = get_settings()
        orig_mock_mode = settings.agent_executor_mock_mode
        settings.agent_executor_mock_mode = False
        executor = AgentExecutor(db, run.id, tool_runner=failing_tool)
        try:
            # Manually trigger tool execution
            await executor._execute_tool_and_process(run, "bad_tool", {"param": 1}, 1)
        finally:
            settings.agent_executor_mock_mode = orig_mock_mode
        
        # Check for receipt
        stmt = select(AgentRunReceipt).where(AgentRunReceipt.run_id == run.id)
        res = await db.execute(stmt)
        receipt = res.scalar_one_or_none()
        
        assert receipt is not None
        assert receipt.receipt_data["success"] is False
        assert "Tool exploded" in receipt.receipt_data["failure_reason"]

@pytest.mark.asyncio
async def test_replay_mode_is_side_effect_free(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        tool_called = False
        async def tracking_tool(name, inputs):
            nonlocal tool_called
            tool_called = True
            return {"ok": True}

        # Executor in replay mode
        executor = AgentExecutor(db, run.id, tool_runner=tracking_tool, is_replay=True)
        
        # Try to execute tool
        await executor._execute_tool_and_process(run, "any_tool", {}, 1)
        
        assert tool_called is False
        
        # Try to continue plan
        from app.models.agents.agents import AgentPlan
        plan = AgentPlan(id=uuid.uuid4(), agent_run_id=run.id, goal_hash="G", status="executing")
        db.add(plan)
        await db.commit()
        
        res = await executor._continue_plan_execution(run, plan)
        assert res is False # Should stop in replay


@pytest.mark.asyncio
async def test_gateway_client_resolution_eager_loads_billing_plan(test_db):
    session_factory = test_db
    async with session_factory() as db:
        from app.models.agents.agents import AgentRun
        from app.models.billing.billing_plan import BillingPlan
        from app.models.core.client import Client

        plan = BillingPlan(
            code="test-plan",
            name="Test Plan",
            rate_limit_per_minute=10,
            daily_token_quota=50000,
            monthly_token_quota=500000,
            max_output_tokens=512,
            allow_streaming=True,
            is_active=True,
        )
        client = Client(
            name="tenant-a",
            billing_plan=plan,
            billing_status="active",
        )
        run = AgentRun(
            id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            tenant_id="tenant-a",
            status="running",
            input_text="X",
            total_steps=0,
            total_tokens=0,
            estimated_cost_brl=0.0,
        )
        db.add(plan)
        db.add(client)
        db.add(run)
        await db.commit()

        provider = GatewayAgentLLMProvider(db, proxy=object())
        resolved = await provider._resolve_client(run)
        assert resolved.id == client.id
        assert resolved.billing_plan is not None
