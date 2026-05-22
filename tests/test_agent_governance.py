import pytest
import uuid
from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision
from app.services.agents.agent_risk_engine import AgentRiskEngine
from app.services.agents import agent_state
from app.models.agents import AgentDefinition, AgentRun

@pytest.mark.asyncio
async def test_policy_destructive_tool_requires_approval(session):
    engine = AgentPolicyEngine(session)
    agent = AgentDefinition(id=uuid.uuid4(), name="Test", risk_level="low", allowed_tools=["*"])
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=0)
    
    action = {"task_type": "tool_call", "tool_name": "delete_database"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.REQUIRE_APPROVAL
    assert "destructive" in reason.lower()

@pytest.mark.asyncio
async def test_policy_shell_tool_blocked(session):
    engine = AgentPolicyEngine(session)
    agent = AgentDefinition(id=uuid.uuid4(), name="Test", risk_level="low", allowed_tools=["*"])
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=0)
    
    action = {"task_type": "tool_call", "tool_name": "execute_shell"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.DENY
    assert "shell" in reason.lower()

@pytest.mark.asyncio
async def test_policy_max_steps_by_risk(session):
    engine = AgentPolicyEngine(session)
    # High risk agent (high risk level + many tools)
    agent = AgentDefinition(id=uuid.uuid4(), name="High Risk", risk_level="high", allowed_tools=["t1", "t2", "t3"], max_steps=100)
    
    # Run with 25 steps (limit will be 20 for risk score 36)
    run = AgentRun(agent_id=agent.id, tenant_id="t1", total_steps=25)
    
    action = {"task_type": "model_call"}
    decision, reason = await engine.evaluate_action(agent, run, action)
    
    assert decision == PolicyDecision.DENY
    assert "max steps" in reason.lower()

@pytest.mark.asyncio
async def test_policy_no_production_without_baseline(session):
    engine = AgentPolicyEngine(session)
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
