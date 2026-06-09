import uuid

import pytest
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision


@pytest.mark.asyncio
async def test_policy_destructive_tool_requires_approval(session):
    engine = AgentPolicyEngine(session)
    agent = AgentDefinition(id=uuid.uuid4(), name="Test", version="1", instructions="test", model_id="m", owner="o", risk_level="low", allowed_tools=["*"])
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=0)
    session.add_all([agent, run])
    await session.commit()
    
    action = {"task_type": "tool_call", "tool_name": "delete_database"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.REQUIRE_APPROVAL
    assert "destructive" in reason.lower()

@pytest.mark.asyncio
async def test_policy_shell_tool_blocked(session):
    engine = AgentPolicyEngine(session)
    agent = AgentDefinition(id=uuid.uuid4(), name="Test", version="1", instructions="test", model_id="m", owner="o", risk_level="low", allowed_tools=["*"])
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=0)
    session.add_all([agent, run])
    await session.commit()
    
    action = {"task_type": "tool_call", "tool_name": "execute_shell"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.DENY
    assert "shell" in reason.lower()

@pytest.mark.asyncio
async def test_policy_denies_shell_tool(session):
    engine = AgentPolicyEngine(session)
    agent = AgentDefinition(id=uuid.uuid4(), name="Test Agent", version="1", instructions="test", model_id="m", owner="o", risk_level="low", allowed_tools=["read"])
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=0)
    session.add_all([agent, run])
    await session.commit()
    
    action = {"task_type": "tool_call", "tool_name": "execute_shell"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.DENY
    assert "shell" in reason.lower() or "globally restricted" in reason.lower()

@pytest.mark.asyncio
async def test_policy_no_production_without_baseline(session, settings):
    engine = AgentPolicyEngine(session)
    settings.agent_production_requires_eval_baseline = True
    agent = AgentDefinition(
        id=uuid.uuid4(), 
        name="Prod Agent", 
        version="1", 
        instructions="test", 
        model_id="m1", 
        owner="admin",
        status="active" # production
    )
    session.add(agent)
    await session.commit()
    
    decision, reason = await engine.evaluate_agent_activation(agent)
    
    assert decision == PolicyDecision.DENY
    assert "baseline" in reason.lower()

@pytest.mark.asyncio
async def test_simulate_policy_does_not_execute(session):
    # This is a bit conceptual as simulate_action just calls evaluate_action
    # But it proves the API layer works without a real run record
    engine = AgentPolicyEngine(session)
    
    # Create real agent for simulation
    agent = AgentDefinition(
        id=uuid.uuid4(), 
        name="Sim Agent", 
        version="1", 
        instructions="test", 
        model_id="m1", 
        owner="admin",
        risk_level="low"
    )
    session.add(agent)
    await session.commit()
    
    action = {"task_type": "tool_call", "tool_name": "shell_exec"}
    res = await engine.simulate_action(agent.id, action)
    
    assert res["decision"] == PolicyDecision.DENY
    assert res["simulated"] is True
