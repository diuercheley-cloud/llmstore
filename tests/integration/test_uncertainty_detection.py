import uuid

import pytest
import pytest_asyncio
from app.models.agents.agent_uncertainty import AgentUncertaintyEvent
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.uncertainty.uncertainty_estimator import UncertaintyEstimator
from app.services.agents.uncertainty.uncertainty_policy import UncertaintyPolicyEngine


@pytest.fixture
def agent_id():
    return uuid.uuid4()

@pytest.fixture
def run_id():
    return uuid.uuid4()

@pytest_asyncio.fixture
async def setup_compliance_agent(session, agent_id):
    agent = AgentDefinition(
        id=agent_id,
        name="Compliance Agent",
        version="1.0",
        model_id="test-model",
        owner="test-owner",
        tenant_id="tenant_a",
        instructions="check compliance",
        agent_class="compliance"
    )
    session.add(agent)
    await session.commit()
    return agent

@pytest.mark.asyncio
async def test_baixa_evidencia_aciona_hitl(session, setup_compliance_agent, agent_id, run_id):
    # Mock run
    run = AgentRun(id=run_id, agent_id=agent_id, tenant_id="tenant_a", status="running")
    session.add(run)
    await session.commit()
    
    estimator = UncertaintyEstimator(session)
    policy_engine = UncertaintyPolicyEngine(session)
    
    # Low evidence
    context = {"evidence_score": 0.1, "tool_result_consistency": 1.0}
    estimation = await estimator.estimate(run_id, context)
    
    # Threshold for compliance is 0.9. Estimation should be around (0.1*0.4 + 0.5*0.2 + 1.0*0.4) = 0.04+0.1+0.4 = 0.54
    assert estimation["confidence_score"] < 0.9
    
    action, reason = await policy_engine.apply_policy(agent_id, run_id, estimation)
    assert action == "hitl"
    assert "Escalating to Human-in-the-Loop" in reason

@pytest.mark.asyncio
async def test_contradicao_reduz_confidence(session, setup_compliance_agent, agent_id, run_id):
    estimator = UncertaintyEstimator(session)
    
    # High contradiction
    context = {
        "evidence_score": 0.9, 
        "tool_result_consistency": 0.2, 
        "contradiction_score": 0.8
    }
    estimation = await estimator.estimate(run_id, context)
    
    # base = (0.9*0.4 + 0.5*0.2 + 0.2*0.4) = 0.36 + 0.1 + 0.08 = 0.54
    # penalty = (0.8*0.5) = 0.4
    # score = 0.14
    assert estimation["confidence_score"] < 0.2

@pytest.mark.asyncio
async def test_threshold_por_classe_funciona(session, agent_id):
    # Creative agent
    agent_creative = AgentDefinition(
        id=agent_id,
        name="Creative Agent",
        version="1.0",
        model_id="test-model",
        owner="test-owner",
        tenant_id="tenant_a",
        instructions="be creative",
        agent_class="creative"
    )
    session.add(agent_creative)
    await session.commit()
    
    policy_engine = UncertaintyPolicyEngine(session)
    policy = await policy_engine.get_policy(agent_id)
    assert policy.min_confidence_threshold == 0.4

@pytest.mark.asyncio
async def test_auto_research_disabled_nao_chama_tool(session, setup_compliance_agent, agent_id, run_id):
    # Mock run
    run = AgentRun(id=run_id, agent_id=agent_id, tenant_id="tenant_a", status="running")
    session.add(run)
    await session.commit()

    policy_engine = UncertaintyPolicyEngine(session)
    # Ensure policy has research disabled
    policy = await policy_engine.get_policy(agent_id)
    policy.auto_research_enabled = False
    await session.commit()
    
    context = {"evidence_score": 0.1} # Low confidence
    estimator = UncertaintyEstimator(session)
    estimation = await estimator.estimate(run_id, context)
    
    action, _ = await policy_engine.apply_policy(agent_id, run_id, estimation)
    assert action != "research"

@pytest.mark.asyncio
async def test_confidence_event_registrado(session, setup_compliance_agent, agent_id, run_id):
    # Mock run
    run = AgentRun(id=run_id, agent_id=agent_id, tenant_id="tenant_a", status="running")
    session.add(run)
    await session.commit()

    estimator = UncertaintyEstimator(session)
    policy_engine = UncertaintyPolicyEngine(session)
    
    context = {"evidence_score": 0.9}
    estimation = await estimator.estimate(run_id, context)
    await policy_engine.apply_policy(agent_id, run_id, estimation)
    
    from sqlalchemy.future import select
    stmt = select(AgentUncertaintyEvent).where(AgentUncertaintyEvent.run_id == run_id)
    event = (await session.execute(stmt)).scalar_one_or_none()
    assert event is not None
    assert event.confidence_score > 0.5
