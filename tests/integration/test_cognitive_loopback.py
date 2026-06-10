import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.models.agents.agent_cognitive_loopback import AgentFewShotExample, AgentLearningCandidate
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.cognitive_loopback.learning_promotion_gate import LearningPromotionGate
from app.services.agents.cognitive_loopback.loopback_service import CognitiveLoopbackService


@pytest.fixture
def agent_id():
    return uuid.uuid4()

@pytest.fixture
def run_id():
    return uuid.uuid4()

@pytest_asyncio.fixture
async def setup_agent(session, agent_id):
    agent = AgentDefinition(
        id=agent_id,
        name="Test Agent",
        version="1.0",
        model_id="test-model",
        owner="test-owner",
        tenant_id="tenant_a",
        instructions="test instructions"
    )
    session.add(agent)
    await session.commit()
    return agent

@pytest.mark.asyncio
async def test_feedback_positivo_gera_candidate(session, setup_agent, agent_id, run_id):
    settings = get_settings()
    settings.agent_cognitive_loopback_enabled = True
    settings.agent_feedback_learning_enabled = True
    
    # Mock run
    run = AgentRun(id=run_id, agent_id=agent_id, tenant_id="tenant_a", status="completed", input_text="hello")
    session.add(run)
    await session.commit()
    
    service = CognitiveLoopbackService(session)
    feedback = {"feedback_type": "thumbs_up", "run_id": str(run_id)}
    res = await service.submit_feedback(agent_id, run_id, "tenant_a", feedback)
    
    assert res["status"] == "feedback_recorded"
    
    # Check if candidate was created
    from sqlalchemy.future import select
    stmt = select(AgentLearningCandidate).where(AgentLearningCandidate.agent_id == agent_id)
    candidates = list((await session.execute(stmt)).scalars().all())
    assert len(candidates) == 1
    assert candidates[0].source_run_id == run_id

@pytest.mark.asyncio
async def test_feedback_negativo_nao_vira_fewshot_automaticamente(session, setup_agent, agent_id, run_id):
    settings = get_settings()
    settings.agent_cognitive_loopback_enabled = True
    settings.agent_feedback_learning_enabled = True
    
    service = CognitiveLoopbackService(session)
    feedback = {"feedback_type": "thumbs_down", "run_id": str(run_id)}
    await service.submit_feedback(agent_id, run_id, "tenant_a", feedback)
    
    from sqlalchemy.future import select
    stmt = select(AgentLearningCandidate).where(AgentLearningCandidate.agent_id == agent_id)
    candidates = list((await session.execute(stmt)).scalars().all())
    assert len(candidates) == 0

@pytest.mark.asyncio
async def test_candidate_com_secret_e_bloqueado(session, setup_agent, agent_id):
    gate = LearningPromotionGate(session)
    candidate = AgentLearningCandidate(
        agent_id=agent_id,
        tenant_id="tenant_a",
        candidate_data={"input": "my secret is sk-123456"},
        validation_status="pending"
    )
    session.add(candidate)
    await session.commit()
    
    eval_res = await gate.run_eval(candidate.id)
    assert eval_res["passed"] is False
    assert "failed_secret_detection" in eval_res["checks"]
    assert candidate.validation_status == "rejected"

@pytest.mark.asyncio
async def test_candidate_exige_eval_antes_de_ativar(session, setup_agent, agent_id):
    gate = LearningPromotionGate(session)
    candidate = AgentLearningCandidate(
        agent_id=agent_id,
        tenant_id="tenant_a",
        candidate_data={"input": "safe input"},
        validation_status="pending"
    )
    session.add(candidate)
    await session.commit()
    
    with pytest.raises(ValueError, match="not eligible for approval"):
        await gate.approve_candidate(candidate.id, "reviewer_1")

@pytest.mark.asyncio
async def test_auto_apply_bloqueado_por_default(session, setup_agent, agent_id):
    settings = get_settings()
    settings.agent_auto_apply_learnings = False
    
    gate = LearningPromotionGate(session)
    candidate = AgentLearningCandidate(
        agent_id=agent_id,
        tenant_id="tenant_a",
        candidate_data={"input": "safe input"},
        validation_status="validated"
    )
    session.add(candidate)
    await session.commit()
    
    res = await gate.approve_candidate(candidate.id, "reviewer_1")
    assert res["auto_promoted"] is False
    
    from sqlalchemy.future import select
    stmt = select(AgentFewShotExample).where(AgentFewShotExample.agent_id == agent_id)
    examples = list((await session.execute(stmt)).scalars().all())
    assert len(examples) == 0
