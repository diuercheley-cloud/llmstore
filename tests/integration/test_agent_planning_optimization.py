import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from app.models.agents.agents import (
    AgentDefinition,
    AgentPlan,
    AgentPlanCostEstimate,
    AgentStepCacheEntry,
    AgentTask,
    AgentTool,
)
from app.services.agents import agent_state
from app.services.agents.agent_executor import AgentExecutor
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.planning.cost_aware_planner import CostAwarePlanner
from app.services.agents.planning.step_cache import StepCache
from sqlalchemy import select


@pytest_asyncio.fixture
async def setup_agent(session):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="planning-agent",
        version="1.0.0",
        instructions="Plan and execute.",
        model_id="gpt-4o",
        owner="tester",
        tenant_id="test-tenant",
        status="active"
    )
    session.add(agent)
    await session.commit()
    return agent

@pytest.mark.asyncio
async def test_step_cache_hit_avoids_llm_call(session, setup_agent):
    run = await agent_state.create_agent_run(session, setup_agent.id, "test-tenant", "Goal")
    run.status = "running"
    await session.commit()
    
    # Pre-populate cache
    cache = StepCache(session)
    # The input_data must match exactly what is hashed in _get_llm_decision
    # run.total_steps is 0 initially
    input_data = {"instructions": setup_agent.instructions, "input_text": run.input_text, "steps": 0}
    output_data = {"type": "final", "content": "Cached Answer"}
    await cache.set_cached_step(
        setup_agent.id, 
        "test-tenant", 
        "model_call", 
        input_data, 
        output_data, 
        model_version="gpt-4o"
    )
    await session.commit()
    
    executor = AgentExecutor(session, run.id)
    # Mock reasoning_loop.execute to return a valid dict if it's ever called (it shouldn't be)
    executor.reasoning_loop.execute = AsyncMock(return_value={"type": "final", "usage": {}})
    
    decision = await executor._get_llm_decision(run, setup_agent, 1)
    
    assert decision == output_data
    executor.reasoning_loop.execute.assert_not_called()

@pytest.mark.asyncio
async def test_side_effect_step_not_cached(session, setup_agent):
    # Tool with side effects
    tool = AgentTool(
        id=uuid.uuid4(),
        name="write_db",
        side_effect_level="write",
        category="database",
        input_schema_json={},
        output_schema_json={},
        enabled=True
    )
    session.add(tool)
    await session.commit()
    
    cache = StepCache(session)
    input_data = {"instructions": "...", "input_text": "...", "steps": 1}
    # Decision to call a tool with side effects should not be cached
    output_data = {"type": "tool_call", "tool_name": "write_db", "args": {}}
    
    await cache.set_cached_step(setup_agent.id, "test-tenant", "model_call", input_data, output_data)
    await session.commit()
    
    # Check if entry exists in DB
    stmt = select(AgentStepCacheEntry).where(AgentStepCacheEntry.agent_id == setup_agent.id)
    res = await session.execute(stmt)
    entry = res.scalar_one_or_none()
    
    assert entry is None # Should not be cached due to side effect

@pytest.mark.asyncio
async def test_cache_expiration(session, setup_agent):
    cache = StepCache(session)
    input_data = {"test": "data"}
    output_data = {"res": "ok"}
    
    # Set with expired TTL
    await cache.set_cached_step(
        setup_agent.id, "test-tenant", "model_call", 
        input_data, output_data, ttl_hours=-1
    )
    await session.commit()
    
    cached = await cache.get_cached_step(setup_agent.id, "test-tenant", "model_call", input_data)
    assert cached is None

@pytest.mark.asyncio
async def test_cost_estimate_generated_on_planning(session, setup_agent):
    planner = AgentPlanner(session)
    run = await agent_state.create_agent_run(session, setup_agent.id, "test-tenant", "Goal")
    
    tasks = [
        {"title": "Search", "task_type": "tool_call"},
        {"title": "Summarize", "task_type": "model_call"}
    ]
    
    plan = await planner.create_plan(run.id, "Goal", tasks)
    
    # Verify estimate exists
    stmt = select(AgentPlanCostEstimate).where(AgentPlanCostEstimate.plan_id == plan.id)
    res = await session.execute(stmt)
    estimate = res.scalar_one_or_none()
    
    assert estimate is not None
    assert estimate.total_estimated_cost_brl > 0
    assert estimate.estimated_tokens > 0

@pytest.mark.asyncio
async def test_low_budget_chooses_cheap_plan(session, setup_agent):
    cost_planner = CostAwarePlanner(session)
    
    # Create two plans
    plan1 = AgentPlan(id=uuid.uuid4(), agent_run_id=uuid.uuid4(), goal_hash="h1", status="draft") # Cheap
    plan2 = AgentPlan(id=uuid.uuid4(), agent_run_id=uuid.uuid4(), goal_hash="h2", status="draft") # Expensive
    session.add_all([plan1, plan2])
    await session.flush()
    
    # Cheap tasks
    session.add(AgentTask(plan_id=plan1.id, title="Quick", task_type="model_call", description_hash="d1"))
    # Expensive tasks (many tasks)
    for i in range(5):
        session.add(AgentTask(plan_id=plan2.id, title=f"Slow {i}", task_type="tool_call", description_hash=f"d2-{i}"))
    
    await session.commit()
    
    optimal = await cost_planner.choose_optimal_plan([plan1, plan2])
    assert optimal.id == plan1.id
