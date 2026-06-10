import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from app.services.agents import agent_runtime
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agents import AgentDefinition
from app.models.agents.multi_agent import (
    AgentSharedWorkspace,
    AgentTeamDelegation,
    AgentTeamMessage,
    AgentTeamRun,
)
from app.services.agents.multi_agent.debate_runtime import DebateRuntime
from app.services.agents.multi_agent.dynamic_runtime import DynamicRoutingRuntime
from app.services.agents.multi_agent.hierarchical_runtime import HierarchicalRuntime
from app.services.agents.multi_agent.loop_guard import LoopGuard
from app.services.agents.multi_agent.shared_workspace import SharedWorkspace
from app.services.agents.multi_agent.team_registry import TeamRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def deterministic_agent_runtime(monkeypatch):
    async def completed_run(**kwargs):
        return SimpleNamespace(
            id=uuid.uuid4(),
            status="completed",
            failure_reason=None,
            estimated_cost_brl=0,
        )

    monkeypatch.setattr(agent_runtime, "start_run", completed_run)


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
    await registry.add_member(team.id, spec1.id, "specialist", {"task_description": "Review auth flow"})
    await db_session.commit()
    
    # 3. Run
    runtime = HierarchicalRuntime(db_session)
    result = await runtime.execute(team.id, "Find vulnerabilities")
    
    assert "Aggregated analysis" in result
    assert "Review auth flow" in result

    run = (
        await db_session.execute(select(AgentTeamRun).where(AgentTeamRun.team_id == team.id))
    ).scalar_one()
    assert run.status == "completed"

    workspace_rows = (
        await db_session.execute(select(AgentSharedWorkspace).where(AgentSharedWorkspace.team_run_id == run.id))
    ).scalars().all()
    assert any(row.key == "manager:summary" for row in workspace_rows)
    assert any(row.key.startswith("specialist:") for row in workspace_rows)

    delegations = (
        await db_session.execute(select(AgentTeamDelegation).where(AgentTeamDelegation.run_id == run.id))
    ).scalars().all()
    assert len(delegations) == 1
    assert delegations[0].status == "completed"

    messages = (
        await db_session.execute(select(AgentTeamMessage).where(AgentTeamMessage.run_id == run.id))
    ).scalars().all()
    assert any(msg.message_type == "instruction" for msg in messages)
    assert any(msg.message_type == "result" for msg in messages)

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
    assert "2 rounds" in result

    run = (
        await db_session.execute(select(AgentTeamRun).where(AgentTeamRun.team_id == team.id))
    ).scalar_one()
    workspace_rows = (
        await db_session.execute(select(AgentSharedWorkspace).where(AgentSharedWorkspace.team_run_id == run.id))
    ).scalars().all()
    keys = {row.key for row in workspace_rows}
    assert {"round:1", "round:2", "synthesizer:summary"}.issubset(keys)

@pytest.mark.asyncio
async def test_dynamic_team_routing_with_recovery(db_session: AsyncSession):
    failing = AgentDefinition(id=uuid.uuid4(), name="Failing", version="1.0.0", instructions="F", owner="test", model_id="gpt-4o")
    backup = AgentDefinition(id=uuid.uuid4(), name="Backup", version="1.0.0", instructions="B", owner="test", model_id="gpt-4o")
    general = AgentDefinition(id=uuid.uuid4(), name="General", version="1.0.0", instructions="G", owner="test", model_id="gpt-4o")
    db_session.add_all([failing, backup, general])
    await db_session.commit()

    registry = TeamRegistry(db_session)
    team = await registry.create_team(
        "t1",
        "Dyn-Team",
        "dynamic",
        "user1",
        config={"work_items": [{"task_id": "auth", "description": "Review auth", "required_capability": "security"}]},
    )
    await registry.add_member(team.id, failing.id, "specialist", {"capabilities": ["security"], "priority": 10, "simulate_failure": True})
    await registry.add_member(team.id, backup.id, "specialist", {"capabilities": ["security"], "priority": 5})
    await registry.add_member(team.id, general.id, "worker", {"capabilities": ["general"], "priority": 1})
    await db_session.commit()

    runtime = DynamicRoutingRuntime(db_session)
    result = await runtime.execute(team.id, "Assess auth posture")

    assert "Dynamic team completed" in result
    assert str(backup.id) in result

    run = (
        await db_session.execute(select(AgentTeamRun).where(AgentTeamRun.team_id == team.id))
    ).scalars().all()[-1]
    workspace_rows = (
        await db_session.execute(select(AgentSharedWorkspace).where(AgentSharedWorkspace.team_run_id == run.id))
    ).scalars().all()
    keys = {row.key for row in workspace_rows}
    assert "dynamic:auth" in keys
    assert "dynamic:summary" in keys

    traces = (
        await db_session.execute(select(AgentTeamMessage).where(AgentTeamMessage.run_id == run.id))
    ).scalars().all()
    assert any(str(backup.id) in msg.content for msg in traces if msg.message_type == "result")

@pytest.mark.asyncio
async def test_loop_detection(db_session: AsyncSession):
    guard = LoopGuard(db_session)
    run_id = uuid.uuid4()
    a1 = uuid.uuid4()
    a2 = uuid.uuid4()
    
    # Simulate delegation A1 -> A2
    from app.models.agents.multi_agent import AgentTeamDelegation
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
