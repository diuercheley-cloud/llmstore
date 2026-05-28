import pytest
import pytest_asyncio
import uuid
from sqlalchemy import select
from app.main import app as main_app
import app.db.session
from app.models.agents import AgentDefinition, AgentRun, AgentPolicyDecision, AgentMemoryPolicy
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.agents.agent_policy_engine import AgentPolicyEngine
from app.db.base import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from pathlib import Path

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-policy-enforcement.db")

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
    orig_mem = settings.agent_memory_enabled
    orig_mem_w = settings.agent_memory_write_enabled
    orig_exec = settings.agent_execution_enabled
    orig_tool_exec = settings.agent_tool_execution_enabled
    orig_handoff = settings.agent_handoffs_enabled
    orig_executor_mock = settings.agent_executor_mock_mode
    
    settings.agent_observability_enabled = True
    settings.agent_memory_enabled = True
    settings.agent_memory_write_enabled = True
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_handoffs_enabled = True
    settings.agent_executor_mock_mode = True
    
    yield
    
    settings.agent_observability_enabled = orig_obs
    settings.agent_memory_enabled = orig_mem
    settings.agent_memory_write_enabled = orig_mem_w
    settings.agent_execution_enabled = orig_exec
    settings.agent_tool_execution_enabled = orig_tool_exec
    settings.agent_handoffs_enabled = orig_handoff
    settings.agent_executor_mock_mode = orig_executor_mock

@pytest.mark.asyncio
async def test_tool_call_enforces_policy(test_db):
    session_factory = test_db
    async with session_factory() as db:
        from app.models.agents import AgentTool
        tool = AgentTool(
            id=uuid.uuid4(), name="bad_tool", category="retrieval",
            input_schema_json={}, output_schema_json={}, 
            risk_level="high", enabled=True, timeout_seconds=30
        )
        db.add(tool)

        agent = AgentDefinition(
            id=uuid.uuid4(), name="Agent", tenant_id="t1", status="active",
            instructions="I", model_id="m", owner="o", version="1.0.0",
            allowed_tools=["safe_tool"] # 'bad_tool' not allowed
        )
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()

        executor = AgentExecutor(db, run.id)
        
        # Manually trigger restricted tool execution
        await executor._execute_tool_and_process(run, "bad_tool", {}, 1)
        
        # Verify decision was recorded
        stmt = select(AgentPolicyDecision).where(AgentPolicyDecision.run_id == run.id, AgentPolicyDecision.action_type == "tool_call")
        res_dec = await db.execute(stmt)
        decision = res_dec.scalar_one_or_none()
        assert decision is not None
        assert decision.result == "deny"
        assert decision.subject == "bad_tool"

@pytest.mark.asyncio
async def test_memory_write_enforces_policy(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="A", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()
        
        from app.services.agents.agent_memory import AgentMemoryService
        memory = AgentMemoryService(db)
        
        # Should fail as no memory policy exists
        with pytest.raises(ValueError, match="no active retention policy"):
            await memory.write_memory(tenant_id="t1", agent_id=agent.id, memory_type="short_term", content="secret", run_id=run.id)

@pytest.mark.asyncio
async def test_planner_exec_enforces_policy(test_db):
    session_factory = test_db
    async with session_factory() as db:
        # Create memory policy to allow final decision memory write
        mem_policy = AgentMemoryPolicy(tenant_id="t1", memory_type="short_term", retention_days=7)
        db.add(mem_policy)

        agent = AgentDefinition(id=uuid.uuid4(), name="A", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0", risk_level="low")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="queued", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(run)
        await db.commit()
        
        executor = AgentExecutor(db, run.id)
        await executor.execute_step()
        
        stmt = select(AgentPolicyDecision).where(AgentPolicyDecision.run_id == run.id, AgentPolicyDecision.action_type == "planner_exec")
        res = await db.execute(stmt)
        decision = res.scalar_one_or_none()
        assert decision is not None
        assert decision.result == "allow"

@pytest.mark.asyncio
async def test_handoff_enforces_policy(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="A", tenant_id="t1", status="active", instructions="I", model_id="m", owner="o", version="1.0.0", risk_level="critical")
        target = AgentDefinition(id=uuid.uuid4(), name="B", tenant_id="t1", status="deprecated", instructions="I", model_id="m", owner="o", version="1.0.0")
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="X", total_steps=0, total_tokens=0, estimated_cost_brl=0.0)
        db.add(agent)
        db.add(target)
        db.add(run)
        await db.commit()
        
        from app.services.agents.agent_handoffs import AgentHandoffService
        handoff = AgentHandoffService(db)
        
        # High risk agent to deprecated target should be denied
        from app.services.agents.agent_handoffs import HandoffDeniedError
        with pytest.raises(HandoffDeniedError, match="denied by policy"):
            await handoff.initiate_handoff(run.id, target.id, "reason", {})

        stmt = select(AgentPolicyDecision).where(AgentPolicyDecision.action_type == "handoff")
        res = await db.execute(stmt)
        decision = res.scalar_one_or_none()
        assert decision.result == "deny"
