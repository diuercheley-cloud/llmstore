import uuid
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import (
    AgentRun,
    AgentRunReceipt,
)
from app.services.agents import agent_runtime, agent_state
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.agents.agent_runtime import ReplayDisabledError, RuntimeDisabledError
from app.services.agents.tool_registry import create_tool
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_and_activate_agent(admin_client: AsyncClient, admin_token_headers, monkeypatch):
    # Enable runtime via feature flags
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    get_settings.cache_clear()

    # 1. Create a draft agent definition
    payload = {
        "name": "Test Helper Agent",
        "version": "1.0.0",
        "description": "Agent for testing runtime admin endpoints",
        "instructions": "Help the user solve problems.",
        "model_id": "mock-llama-3",
        "owner": "test-suite",
        "tenant_id": "tenant-123",
        "status": "draft",
        "risk_level": "medium",
        "allowed_tools": ["calculator", "web_search"],
        "max_steps": 5,
        "max_runtime_seconds": 120,
    }

    resp = await admin_client.post("/admin/agents", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Helper Agent"
    assert data["status"] == "draft"
    agent_id = data["id"]

    # 2. Patch the agent definition
    patch_payload = {
        "description": "Updated description",
        "risk_level": "low",
    }
    resp = await admin_client.patch(f"/admin/agents/{agent_id}", json=patch_payload, headers=admin_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Updated description"
    assert data["risk_level"] == "low"

    # 3. Activate the agent
    resp = await admin_client.post(f"/admin/agents/{agent_id}/activate", headers=admin_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"

    # 4. Deprecate the agent
    resp = await admin_client.post(f"/admin/agents/{agent_id}/deprecate", headers=admin_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deprecated"


@pytest.mark.asyncio
async def test_execute_agent_mock_success(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "false")
    monkeypatch.setenv("AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    # Register calculator tool
    await create_tool(session, {
        "name": "calculator",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    # Create agent definition
    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Math Agent",
            "version": "1.0.0",
            "instructions": "Resolve math operations using tools.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
            "allowed_tools": ["calculator"],
            "max_steps": 10,
            "max_runtime_seconds": 300,
        }
    )

    # Pre-define LLM response sequence
    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "final", "output": "The response is 4"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    # Tool runner mock
    tool_calls = []
    async def mock_tool_runner(name, tool_input):
        clean_input = {k: v for k, v in tool_input.items() if k not in ("db", "tenant_id", "agent_id", "run_id")}
        tool_calls.append((name, clean_input))
        if name == "calculator":
            return {"result": 4}
        return {"error": "unknown tool"}

    # Start the agent run
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="What is 2+2?",
        llm_provider=mock_llm,
        tool_runner=mock_tool_runner,
    )

    # Verify execution ran to completion synchronously
    assert run.status == "completed"
    assert run.total_steps >= 2
    assert run.output_hash == agent_state.compute_sha256("The response is 4")
    assert len(tool_calls) == 1
    assert tool_calls[0] == ("calculator", {"expression": "2+2"})


@pytest.mark.asyncio
async def test_execute_agent_runtime_disabled(admin_client: AsyncClient, admin_token_headers, monkeypatch, session):
    # Disable runtime via feature flags
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "false")
    get_settings.cache_clear()

    # Verify FastAPI endpoint returns 400
    payload = {
        "tenant_id": "tenant-abc",
        "input_text": "hello",
    }
    dummy_uuid = uuid.uuid4()
    resp = await admin_client.post(f"/agents/{dummy_uuid}/runs", json=payload, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Agent runtime is disabled" in resp.json()["detail"]

    # Verify python API raises RuntimeDisabledError
    with pytest.raises(RuntimeDisabledError):
        await agent_runtime.start_run(
            db=session,
            agent_id=dummy_uuid,
            tenant_id="tenant-abc",
            input_text="hello",
        )


@pytest.mark.asyncio
async def test_execute_agent_execution_disabled_fails_without_simulation_override(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "false")  # execution disabled
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "false") # Must be false to trigger real execution check
    monkeypatch.setenv("AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION", "true")
    get_settings.cache_clear()

    # Register calculator tool
    await create_tool(session, {
        "name": "calculator",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Math Agent 2",
            "version": "1.0.0",
            "instructions": "Resolve math.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
            "allowed_tools": ["calculator"],
        }
    )

    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "final", "output": "done"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="What is 2+2?",
        llm_provider=mock_llm,
    )

    assert run.status == "failed"
    assert "Agent execution is disabled" in run.failure_reason


@pytest.mark.asyncio
async def test_pause_resume_cancel_run(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "false")
    monkeypatch.setenv("AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    # Register tool
    await create_tool(session, {
        "name": "calculator",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Pause Agent",
            "version": "1.0.0",
            "instructions": "Wait.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
            "allowed_tools": ["calculator"],
        }
    )

    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "final", "output": "ended"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    # Tool runner pauses the run mid-way
    async def mock_tool_runner(name, tool_input):
        r_id = tool_input.get("run_id")
        await agent_runtime.pause_run(session, r_id)
        return {"result": 4}

    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="Calculate",
        llm_provider=mock_llm,
        tool_runner=mock_tool_runner,
    )

    # Loop should have broken since state changed to paused
    assert run.status == "paused"

    # Now let's resume execution.
    async def mock_tool_runner_resume(name, tool_input):
        return {"result": 4}

    # Resume the execution run
    resumed_run = await agent_runtime.resume_run(
        db=session,
        run_id=run.id,
        llm_provider=mock_llm,
        tool_runner=mock_tool_runner_resume,
    )
    assert resumed_run.status == "completed"

    # Verify cancel run transition
    llm_responses_cancel = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
    ]
    mock_llm_cancel = MockLLMProvider(responses=llm_responses_cancel)
    
    async def mock_tool_runner_cancel(name, tool_input):
        r_id = tool_input.get("run_id")
        await agent_runtime.cancel_run(session, r_id)
        return {"result": 4}

    run_cancel = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="Calculate and cancel",
        llm_provider=mock_llm_cancel,
        tool_runner=mock_tool_runner_cancel,
    )

    assert run_cancel.status == "cancelled"


@pytest.mark.asyncio
async def test_replay_run(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_REPLAY_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Replay Agent",
            "version": "1.0.0",
            "instructions": "Reply.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
        }
    )

    llm_responses = [
        {"type": "final", "output": "4"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="replay test",
        llm_provider=mock_llm,
    )

    assert run.status == "completed"

    # Replay the run
    replay_data = await agent_runtime.replay_run(session, run.id)
    assert replay_data["run_id"] == run.id
    assert replay_data["status"] == "completed"

    # Disable replay and check for error
    monkeypatch.setenv("AGENT_REPLAY_ENABLED", "false")
    get_settings.cache_clear()
    with pytest.raises(ReplayDisabledError):
        await agent_runtime.replay_run(session, run.id)


@pytest.mark.asyncio
async def test_max_steps_limit(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

    # Register tool
    await create_tool(session, {
        "name": "calculator",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Limited Step Agent",
            "version": "1.0.0",
            "instructions": "Loop forever.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
            "max_steps": 2,
            "allowed_tools": ["calculator"]
        }
    )

    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {}},
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {}},
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {}},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="infinite loop",
        llm_provider=mock_llm,
    )

    assert run.status == "failed"
    assert "Max steps exceeded" in run.failure_reason


@pytest.mark.asyncio
async def test_max_runtime_seconds_limit(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

    # Register tool
    await create_tool(session, {
        "name": "calculator",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Timed Out Agent",
            "version": "1.0.0",
            "instructions": "Loop.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
            "max_runtime_seconds": 1,
            "allowed_tools": ["calculator"]
        }
    )

    run = await agent_state.create_agent_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="timeout test",
    )
    
    run.started_at = utc_now() - timedelta(seconds=5)
    await session.commit()

    executor = AgentExecutor(session, run.id)
    should_continue = await executor.execute_step()

    assert not should_continue
    await session.refresh(run)
    assert run.status == "failed"
    assert "Max runtime exceeded" in run.failure_reason


@pytest.mark.asyncio
async def test_prompt_logs_masking(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "Masking Agent",
            "version": "1.0.0",
            "instructions": "Do not leak secret_instruction_key",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-abc",
            "status": "active",
        }
    )

    llm_responses = [
        {"type": "final", "output": "Top secret output details"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    input_text = "My secret query: secret_query_value"
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text=input_text,
        llm_provider=mock_llm,
    )

    assert run.status == "completed"

    steps = await agent_state.get_run_steps(session, run.id)
    assert len(steps) == 1
    step = steps[0]
    
    expected_input_hash = agent_state.compute_sha256({"input_hash": run.input_hash})
    assert step.input_hash == expected_input_hash
    
    # Make sure they don't contain the raw prompt texts anywhere in step columns
    for col in ["input_hash", "output_hash", "error"]:
        val = getattr(step, col, None)
        if val:
            assert "secret_query_value" not in str(val)
            assert "secret_instruction_key" not in str(val)
            assert "Top secret output details" not in str(val)
