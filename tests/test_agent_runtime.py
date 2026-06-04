import uuid
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentRun,
    AgentRunReceipt,
)
from app.services.agents import agent_runtime, agent_state
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.agents.agent_runtime import ReplayDisabledError, RuntimeDisabledError
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
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

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
        tool_calls.append((name, tool_input))
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
    assert run.total_steps == 3  # step 1 (model_call), step 2 (tool_call), step 3 (final)
    assert run.output_hash == agent_state.compute_sha256("The response is 4")
    assert len(tool_calls) == 1
    assert tool_calls[0] == ("calculator", {"expression": "2+2"})

    # Check that steps were registered in DB
    steps = await agent_state.get_run_steps(session, run.id)
    assert len(steps) == 3
    assert steps[0].step_type == "model_call"
    assert steps[1].step_type == "tool_call"
    assert steps[2].step_type == "final"

    # Check checkpoints
    checkpoints = await agent_state.get_run_checkpoints(session, run.id)
    assert len(checkpoints) == 2  # before and after tool call
    assert checkpoints[0].state_snapshot["status"] == "before_tool_call"
    assert checkpoints[1].state_snapshot["status"] == "after_tool_call"

    # Check receipts
    receipts_res = await session.execute(
        select(AgentRunReceipt).where(AgentRunReceipt.run_id == run.id)
    )
    receipts = list(receipts_res.scalars().all())
    assert len(receipts) == 1
    assert receipts[0].receipt_data["tool_name"] == "calculator"
    assert receipts[0].signature is not None


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
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

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

    tool_executed = False
    async def mock_tool_runner(name, tool_input):
        nonlocal tool_executed
        tool_executed = True
        return {"result": 4}

    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="What is 2+2?",
        llm_provider=mock_llm,
        tool_runner=mock_tool_runner,
    )

    assert run.status == "failed"
    assert not tool_executed  # Real tool MUST NOT execute
    assert "Agent execution is disabled" in run.failure_reason


@pytest.mark.asyncio
async def test_pause_resume_cancel_run(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

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
        # Pause execution run in DB
        res = await session.execute(
            select(AgentRun).where(AgentRun.status == "running")
        )
        active_run = res.scalar_one()
        await agent_runtime.pause_run(session, active_run.id)
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

    # Now let's resume execution. Provide another tool runner that doesn't pause.
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
    # 1. Create a new run
    llm_responses_cancel = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
    ]
    mock_llm_cancel = MockLLMProvider(responses=llm_responses_cancel)
    
    async def mock_tool_runner_cancel(name, tool_input):
        res = await session.execute(
            select(AgentRun).where(AgentRun.status == "running")
        )
        active_run = res.scalar_one()
        await agent_runtime.cancel_run(session, active_run.id)
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
            "allowed_tools": ["calculator"],
        }
    )

    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
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
    assert len(replay_data["steps"]) == 3
    assert len(replay_data["checkpoints"]) == 2

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
            "max_steps": 2,  # Limit to 2 steps max!
        }
    )

    # LLM always asks to run a tool, causing loop
    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
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
    assert run.failure_reason == "Max steps exceeded"


@pytest.mark.asyncio
async def test_max_runtime_seconds_limit(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "true")
    get_settings.cache_clear()

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
            "max_runtime_seconds": 1,  # 1 second max runtime
        }
    )

    llm_responses = [
        {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}},
        {"type": "final", "output": "done"},
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    # Let's create a custom executor or inject a start time offset
    # Start the run
    run = await agent_state.create_agent_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-abc",
        input_text="timeout test",
    )
    
    # Backdate the run started_at time to 5 seconds ago (exceeding the 1 second limit)
    run.started_at = utc_now() - timedelta(seconds=5)
    await session.commit()

    # Instantiate executor and execute a step
    executor = AgentExecutor(session, run.id, mock_llm)
    should_continue = await executor.execute_step()

    # The step execution should have terminated and failed due to timeout
    assert not should_continue
    await session.refresh(run)
    assert run.status == "failed"
    assert "Max runtime seconds exceeded" in run.failure_reason


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

    # Query the steps and runs from the DB
    steps = await agent_state.get_run_steps(session, run.id)
    assert len(steps) == 1
    
    # Assert step does not contain the raw input/output texts in its fields
    # Let's inspect step object attributes
    step = steps[0]
    # Check that hashes are correctly computed
    assert step.input_hash == agent_state.compute_sha256({"prompt_hash": run.input_hash})
    assert step.output_hash == agent_state.compute_sha256({"output_hash": agent_state.compute_sha256("Top secret output details")})
    
    # Make sure they don't contain the raw prompt texts anywhere in step columns
    for col in ["input_hash", "output_hash", "error"]:
        val = getattr(step, col, None)
        if val:
            assert "secret_query_value" not in str(val)
            assert "secret_instruction_key" not in str(val)
            assert "Top secret output details" not in str(val)
