import uuid
from unittest.mock import MagicMock

import pytest
from app.services.agents import agent_state
from app.services.agents.agent_executor import AgentExecutor
from prometheus_client import REGISTRY


@pytest.mark.asyncio
async def test_agent_observability_metrics_increment(session):
    # Setup
    agent_id = uuid.uuid4()
    tenant_id = "test-tenant"

    # Create agent definition
    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Obs Test Agent",
            "version": "1.0.0",
            "instructions": "Test instructions",
            "model_id": "gpt-4",
            "owner": "admin",
            "tenant_id": tenant_id,
        },
    )

    # Create run
    run = await agent_state.create_agent_run(session, agent_def.id, tenant_id, "hello")

    # Mock LLM Provider
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value={"type": "final", "output": "done"})

    # Execute step
    executor = AgentExecutor(session, run.id, llm_provider=mock_llm)

    # Check initial metric value
    before = (
        REGISTRY.get_sample_value(
            "llm_agent_runs_total", {"agent_id": str(agent_def.id), "status": "started"}
        )
        or 0
    )

    await executor.execute_step()

    # Check if metrics were incremented
    after_started = REGISTRY.get_sample_value(
        "llm_agent_runs_total", {"agent_id": str(agent_def.id), "status": "started"}
    )
    after_completed = REGISTRY.get_sample_value(
        "llm_agent_runs_total", {"agent_id": str(agent_def.id), "status": "completed"}
    )

    assert after_started == before + 1
    assert after_completed == 1


@pytest.mark.asyncio
async def test_agent_timeline_ordering(session):
    # Setup
    agent_id = uuid.uuid4()
    tenant_id = "test-tenant"

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Timeline Agent",
            "version": "1.0.0",
            "instructions": "Test",
            "model_id": "gpt-4",
            "owner": "admin",
            "tenant_id": tenant_id,
        },
    )

    run = await agent_state.create_agent_run(session, agent_def.id, tenant_id, "hello")

    # Manually log some steps
    await agent_state.log_run_step(session, run.id, 1, "model_call", "in1", "out1", latency_ms=100)
    await agent_state.log_run_step(session, run.id, 2, "tool_call", "in2", "out2", latency_ms=200)

    # Fetch timeline via API-like logic
    from app.api.agent_observability_admin import get_run_timeline

    # Mock admin user
    admin_user = MagicMock()

    timeline = await get_run_timeline(run.id, session, admin_user)

    assert len(timeline) == 2
    assert timeline[0]["step_number"] == 1
    assert timeline[1]["step_number"] == 2
    assert timeline[0]["timestamp"] <= timeline[1]["timestamp"]


@pytest.mark.asyncio
async def test_trace_masking(session):
    # Setup
    agent_id = uuid.uuid4()
    tenant_id = "secret-tenant"

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Masking Agent",
            "version": "1.0.0",
            "instructions": "Test",
            "model_id": "gpt-4",
            "owner": "admin",
            "tenant_id": tenant_id,
        },
    )

    run = await agent_state.create_agent_run(session, agent_def.id, tenant_id, "top secret input")

    from app.api.agent_observability_admin import get_run_trace

    admin_user = MagicMock()

    trace = await get_run_trace(run.id, session, admin_user)

    # Check if prompt is masked (not present in attributes)
    # The attributes should contain hashed tenant if export enabled, or raw if not.
    # But it should definitely NOT contain the raw input text.
    attrs = trace["attributes"]
    assert "input_text" not in attrs
    assert "top secret input" not in str(attrs)
