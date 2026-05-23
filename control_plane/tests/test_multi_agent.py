import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.agents import AgentDefinition
from app.services.agents.multi_agent.team_registry import TeamRegistry
from app.services.agents.multi_agent.hierarchical_runtime import HierarchicalRuntime
from app.services.agents.multi_agent.debate_runtime import DebateRuntime
from app.services.agents.multi_agent.loop_guard import LoopGuard
from app.services.agents.multi_agent.shared_workspace import SharedWorkspace

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents
        import app.models.multi_agent
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session

@pytest.mark.asyncio
async def test_hierarchical_team_execution(db_session: AsyncSession):
    # 1. Create Agents
    manager = AgentDefinition(id=uuid.uuid4(), name="Manager", version="1.0.0", instructions="M", owner="test", model_id="gpt-4o")
    spec1 = AgentDefinition(id=uuid.uuid4(), name="Spec 1", version="1.0.0", instructions="S1", owner="test", model_id="gpt-4o")
    db_session.add_all([manager, spec1])
    await db_session.commit()
    
    # 2. Create Team
    registry = TeamRegistry(db_session)
    team = await registry.create_team("t1", "H-Team", "hierarchical", "user1")
    await registry.add_member(team.id, manager.id, "manager")
    await registry.add_member(team.id, spec1.id, "specialist")
    await db_session.commit()
    
    # 3. Run
    runtime = HierarchicalRuntime(db_session)
    result = await runtime.execute(team.id, "Find vulnerabilities")
    
    assert "Aggregated analysis" in result
    assert "completed task" in result

@pytest.mark.asyncio
async def test_debate_team_execution(db_session: AsyncSession):
    # 1. Create Agents
    p1 = AgentDefinition(id=uuid.uuid4(), name="P1", version="1.0.0", instructions="P", owner="test", model_id="gpt-4o")
    c1 = AgentDefinition(id=uuid.uuid4(), name="C1", version="1.0.0", instructions="C", owner="test", model_id="gpt-4o")
    s1 = AgentDefinition(id=uuid.uuid4(), name="S1", version="1.0.0", instructions="S", owner="test", model_id="gpt-4o")
    db_session.add_all([p1, c1, s1])
    await db_session.commit()
    
    # 2. Create Team
    registry = TeamRegistry(db_session)
    team = await registry.create_team("t1", "D-Team", "debate", "user1")
    await registry.add_member(team.id, p1.id, "proposer")
    await registry.add_member(team.id, c1.id, "critic")
    await registry.add_member(team.id, s1.id, "synthesizer")
    await db_session.commit()
    
    # 3. Run
    runtime = DebateRuntime(db_session)
    result = await runtime.execute(team.id, "Optimal budget", max_rounds=2)
    
    assert "Final synthesized answer" in result

@pytest.mark.asyncio
async def test_loop_detection(db_session: AsyncSession):
    guard = LoopGuard(db_session)
    run_id = uuid.uuid4()
    a1 = uuid.uuid4()
    a2 = uuid.uuid4()
    
    # Simulate delegation A1 -> A2
    from app.models.multi_agent import AgentTeamDelegation
    del1 = AgentTeamDelegation(run_id=run_id, parent_agent_id=a1, child_agent_id=a2, task_description="T1", status="active")
    db_session.add(del1)
    await db_session.commit()
    
    # Check cycle A2 -> A1
    assert await guard.detect_cycle(run_id, a2, a1) is True
    # Check no cycle A1 -> A3
    assert await guard.detect_cycle(run_id, a1, uuid.uuid4()) is False

@pytest.mark.asyncio
async def test_shared_workspace_isolation(db_session: AsyncSession):
    ws = SharedWorkspace(db_session, "tenant1")
    run_id = uuid.uuid4()
    
    await ws.put(run_id, "key1", {"data": 123})
    val = await ws.get(run_id, "key1")
    assert val == {"data": 123}
    
    # Check different run
    assert await ws.get(uuid.uuid4(), "key1") is None

import pytest_asyncio
