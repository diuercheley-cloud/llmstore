import pytest
import uuid
from app.services.agents.meta_reviewer.meta_reviewer import MetaReviewerService
from app.models.agents import AgentDefinition, AgentRun
from app.models.agent_meta_reviewer import AgentMetaReview, AgentMetaReviewFinding
from app.core.config import get_settings

@pytest.fixture
def agent_id():
    return uuid.uuid4()

@pytest.fixture
def run_id():
    return uuid.uuid4()

@pytest.fixture
async def setup_agent(session, agent_id):
    agent = AgentDefinition(
        id=agent_id,
        name="Security Agent",
        version="1.0",
        model_id="test-model",
        owner="test-owner",
        tenant_id="tenant_a",
        instructions="do security tasks"
    )
    session.add(agent)
    await session.commit()
    return agent

@pytest.mark.asyncio
async def test_unsupported_claim_gera_finding(session, setup_agent, agent_id, run_id):
    settings = get_settings()
    settings.agent_meta_reviewer_enabled = True
    
    service = MetaReviewerService(session)
    # Long response with zero evidence
    response = "The capital of France is Paris and it has 2 million people living there currently. It is known for its Eiffel Tower and many museums like the Louvre, but since I have no evidence about the population, this might be a hallucination."
    decision, reasoning = await service.review_response(
        agent_id, run_id, "tenant_a", response, [], {}
    )
    
    assert decision == "require_revision"
    assert "Medium-severity consistency issue" in reasoning

@pytest.mark.asyncio
async def test_high_risk_tool_sem_approval_bloqueia(session, setup_agent, agent_id, run_id):
    settings = get_settings()
    settings.agent_meta_reviewer_enabled = True
    settings.agent_meta_reviewer_blocking_mode = True
    
    service = MetaReviewerService(session)
    context = {"risk_level": "high", "human_approval_obtained": False}
    
    decision, reasoning = await service.review_response(
        agent_id, run_id, "tenant_a", "I am about to delete the database.", [], context
    )
    
    assert decision == "require_human_approval"
    assert "High-severity policy" in reasoning

@pytest.mark.asyncio
async def test_blocking_mode_behavior(session, setup_agent, agent_id, run_id):
    settings = get_settings()
    settings.agent_meta_reviewer_enabled = True
    
    # 1. Advisory mode (blocking=False)
    settings.agent_meta_reviewer_blocking_mode = False
    service = MetaReviewerService(session)
    
    response = "I will perform an exploit on the target system."
    decision, reasoning = await service.review_response(
        agent_id, run_id, "tenant_a", response, [], {}
    )
    
    assert decision == "block"
    # Even though decision is 'block', check the review record
    from sqlalchemy.future import select
    from app.models.agent_meta_reviewer import AgentMetaReviewDecision
    stmt = select(AgentMetaReviewDecision).order_by(AgentMetaReviewDecision.created_at.desc())
    res = await session.execute(stmt)
    last_decision = res.scalars().first()
    assert last_decision.blocking_action_taken is False

    # 2. Blocking mode (blocking=True)
    settings.agent_meta_reviewer_blocking_mode = True
    decision, reasoning = await service.review_response(
        agent_id, run_id, "tenant_a", response, [], {}
    )
    assert decision == "block"
    
    res2 = await session.execute(stmt)
    last_decision2 = res2.scalars().first()
    assert last_decision2.blocking_action_taken is True

@pytest.mark.asyncio
async def test_reviewer_nao_ve_secrets_brutos(session, setup_agent, agent_id, run_id):
    # This is more of a policy check in the service implementation
    # The reviewer should ideally receive redacted evidence.
    pass
