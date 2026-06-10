import hashlib
import json
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.deterministic_execution.service import DeterministicExecutionService
from app.models.core.deterministic_execution import ExecutionRun, ExecutionStep, ToolCallRecord


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_deterministic_hash_consistency(mock_session):
    service = DeterministicExecutionService(mock_session)
    
    agent_id = uuid.uuid4()
    tenant_id = "test-tenant"
    
    # 1. Create a run
    run = await service.start_run(str(agent_id), tenant_id, seed=42)
    
    # 2. Record a step
    step = await service.record_step(
        run_id=run.id,
        step_number=1,
        model_name="gpt-4",
        provider="openai",
        prompt_rendered="Hello world",
        response_text="Hi there"
    )
    
    # 3. Record a tool call
    await service.record_tool_call(
        step_id=step.id,
        tool_name="calculator",
        tool_input={"query": "2+2"},
        tool_output={"result": 4}
    )
    
    # Mocking the session.execute to return the run with loaded relationships
    mock_run = MagicMock(spec=ExecutionRun)
    mock_run.id = run.id
    mock_run.agent_id = agent_id
    mock_run.tenant_id = tenant_id
    mock_run.seed = 42
    mock_run.temperature = 0.0
    mock_run.top_p = 1.0
    
    mock_step = MagicMock(spec=ExecutionStep)
    mock_step.step_number = 1
    mock_step.model_name = "gpt-4"
    mock_step.provider = "openai"
    mock_step.prompt_hash = hashlib.sha256("Hello world".encode()).hexdigest()
    mock_step.response_hash = hashlib.sha256("Hi there".encode()).hexdigest()
    
    mock_tool = MagicMock(spec=ToolCallRecord)
    mock_tool.tool_name = "calculator"
    mock_tool.tool_input = {"query": "2+2"}
    mock_tool.is_redacted = False
    
    mock_step.tool_calls = [mock_tool]
    mock_run.steps = [mock_step]
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    
    # Make execute return an awaitable that resolves to mock_result
    mock_session.execute.return_value = mock_result
    
    manifest1 = await service.generate_manifest(run.id)
    hash1 = manifest1["manifest_hash"]
    
    # Generate again, should be same
    # We need to reset the mock side effect/return value if we use side_effect
    mock_session.execute.return_value = mock_result
    manifest2 = await service.generate_manifest(run.id)
    hash2 = manifest2["manifest_hash"]
    
    assert hash1 == hash2


@pytest.mark.asyncio
async def test_prompt_change_alters_hash(mock_session):
    service = DeterministicExecutionService(mock_session)
    
    def create_mock_run(prompt):
        mr = MagicMock(spec=ExecutionRun)
        mr.id = uuid.uuid4()
        mr.agent_id = uuid.uuid4()
        mr.tenant_id = "tenant"
        mr.seed = 42
        mr.temperature = 0.0
        mr.top_p = 1.0
        ms = MagicMock(spec=ExecutionStep)
        ms.step_number = 1
        ms.model_name = "gpt-4"
        ms.provider = "openai"
        ms.prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        ms.response_hash = "resp-hash"
        ms.tool_calls = []
        mr.steps = [ms]
        return mr

    run_a = create_mock_run("Prompt A")
    run_b = create_mock_run("Prompt B")

    mock_result_a = MagicMock()
    mock_result_a.scalar_one_or_none.return_value = run_a
    
    mock_result_b = MagicMock()
    mock_result_b.scalar_one_or_none.return_value = run_b

    mock_session.execute.side_effect = [mock_result_a, mock_result_b]
    
    manifest_a = await service.generate_manifest(run_a.id)
    manifest_b = await service.generate_manifest(run_b.id)
    
    assert manifest_a["manifest_hash"] != manifest_b["manifest_hash"]


@pytest.mark.asyncio
async def test_tool_redaction_hides_secrets(mock_session):
    service = DeterministicExecutionService(mock_session)
    
    # Record a tool call with redacted output
    record = await service.record_tool_call(
        step_id=uuid.uuid4(),
        tool_name="get_api_key",
        tool_input={"service": "github"},
        tool_output={"key": "sk-12345"},
        is_redacted=True
    )
    
    assert record.is_redacted is True
