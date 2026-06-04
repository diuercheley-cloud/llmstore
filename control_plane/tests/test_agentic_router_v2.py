import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.agent_routing import (
    AgentCostQualityProfile,
    AgentModelCapability,
    AgentStepRoutingDecision,
)
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.routing.agentic_router import AgenticRouterV2
from app.services.agents.routing.cost_quality_policy import PolicyType
from app.services.agents.routing.step_classifier import StepClass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use a test-specific SQLite DB
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def setup_models(db_session: AsyncSession):
    # Register models
    cheap_model = AgentModelCapability(
        model_id="cheap-model",
        provider="local",
        supports_tool_calling=True,
        supports_json_mode=True,
        context_window=4096,
        cost_input=0.01,
        cost_output=0.02,
        latency_class="ultra-low",
        quality_tier=1,
        recommended_step_classes=[StepClass.FORMATTING, StepClass.CLASSIFICATION]
    )
    expensive_model = AgentModelCapability(
        model_id="expensive-model",
        provider="cloud-high-end",
        supports_tool_calling=True,
        supports_json_mode=True,
        context_window=128000,
        cost_input=1.0,
        cost_output=2.0,
        latency_class="high",
        quality_tier=5,
        recommended_step_classes=[StepClass.COMPLEX_REASONING, StepClass.CODE_GENERATION]
    )
    db_session.add(cheap_model)
    db_session.add(expensive_model)
    await db_session.commit()
    return cheap_model, expensive_model


@pytest_asyncio.fixture
async def setup_agent(db_session: AsyncSession):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Test Agent",
        version="1.0.0",
        instructions="Test",
        model_id="cheap-model",
        owner="test"
    )
    db_session.add(agent)
    await db_session.commit()
    
    run = AgentRun(
        id=uuid.uuid4(),
        agent_id=agent.id,
        tenant_id="test-tenant",
        status="running"
    )
    db_session.add(run)
    await db_session.commit()
    return agent, run


@pytest.mark.asyncio
async def test_routing_formatting_uses_cheap_model(db_session: AsyncSession, setup_models, setup_agent):
    agent, run = setup_agent
    router = AgenticRouterV2(db_session)
    
    model_id = await router.route_step(
        run_id=run.id,
        step_type="model_call",
        input_text="Please format this as JSON",
        policy_name=PolicyType.LOWEST_COST
    )
    
    assert model_id == "cheap-model"
    result = await db_session.execute(select(AgentStepRoutingDecision).filter(AgentStepRoutingDecision.run_id == run.id))
    decision = result.scalars().first()
    assert decision.step_class == StepClass.FORMATTING
    assert "Selected model 'cheap-model'" in decision.explanation


@pytest.mark.asyncio
async def test_routing_complex_reasoning_uses_high_quality_model(db_session: AsyncSession, setup_models, setup_agent):
    agent, run = setup_agent
    router = AgenticRouterV2(db_session)
    
    model_id = await router.route_step(
        run_id=run.id,
        step_type="model_call",
        input_text="Think deeply about the implications of quantum gravity",
        policy_name=PolicyType.HIGH_QUALITY
    )
    
    assert model_id == "expensive-model"
    result = await db_session.execute(select(AgentStepRoutingDecision).filter(AgentStepRoutingDecision.run_id == run.id))
    decision = result.scalars().first()
    assert decision.step_class == StepClass.COMPLEX_REASONING


@pytest.mark.asyncio
async def test_sovereign_only_blocks_cloud_provider(db_session: AsyncSession, setup_models, setup_agent):
    agent, run = setup_agent
    router = AgenticRouterV2(db_session)
    
    # Even for complex reasoning, if sovereign_only is set, it should pick the local one
    model_id = await router.route_step(
        run_id=run.id,
        step_type="model_call",
        input_text="Complex task",
        policy_name=PolicyType.SOVEREIGN_ONLY
    )
    
    assert model_id == "cheap-model"


@pytest.mark.asyncio
async def test_fallback_registers_decision(db_session: AsyncSession, setup_models, setup_agent):
    agent, run = setup_agent
    router = AgenticRouterV2(db_session)
    
    # Force fallback from expensive model
    model_id = await router.route_step(
        run_id=run.id,
        step_type="model_call",
        input_text="Complex task",
        policy_name=PolicyType.HIGH_QUALITY,
        fallback_from_model_id="expensive-model",
        failure_reason="Timeout"
    )
    
    assert model_id == "cheap-model"
    result = await db_session.execute(select(AgentStepRoutingDecision).filter(AgentStepRoutingDecision.run_id == run.id))
    decision = result.scalars().first()
    assert "Fallback occurred" in decision.explanation
    assert "Timeout" in decision.explanation


@pytest.mark.asyncio
async def test_budget_limits_choice(db_session: AsyncSession, setup_models, setup_agent):
    agent, run = setup_agent
    router = AgenticRouterV2(db_session)
    
    # Create a profile with strict budget
    profile = AgentCostQualityProfile(
        name="strict-budget",
        max_cost_input=0.1
    )
    db_session.add(profile)
    await db_session.commit()
    
    # Even if we ask for high quality, if it's too expensive, it should be filtered out
    # If no models match, it currently raises ValueError in route_step
    # Let's see if it picks the cheap one if it's the only one under budget
    
    model_id = await router.route_step(
        run_id=run.id,
        step_type="model_call",
        input_text="Complex task",
        policy_name=PolicyType.HIGH_QUALITY,
        profile_name="strict-budget"
    )
    
    assert model_id == "cheap-model"
