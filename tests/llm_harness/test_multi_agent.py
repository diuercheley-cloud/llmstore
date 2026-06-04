import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.multi_agent import MultiAgentOrchestrator, _safe_parse_json


class TestSafeParseJson:
    def test_direct_json_object(self):
        result = _safe_parse_json('{"status": "approved", "feedback": "good"}')
        assert result == {"status": "approved", "feedback": "good"}

    def test_direct_json_array(self):
        result = _safe_parse_json('[{"type": "write_file", "path": "x.txt"}]')
        assert result == [{"type": "write_file", "path": "x.txt"}]

    def test_json_in_code_fence(self):
        result = _safe_parse_json('```json\n{"status": "approved"}\n```')
        assert result == {"status": "approved"}

    def test_json_in_plain_code_fence(self):
        result = _safe_parse_json('```\n{"status": "rejected", "feedback": "fix it"}\n```')
        assert result == {"status": "rejected", "feedback": "fix it"}

    def test_json_with_text_before(self):
        result = _safe_parse_json('Here is my decision:\n```json\n{"next_agent": "developer"}\n```\nGood luck!')
        assert result == {"next_agent": "developer"}

    def test_json_single_quotes(self):
        result = _safe_parse_json("{'status': 'approved', 'feedback': 'ok'}")
        assert result == {"status": "approved", "feedback": "ok"}

    def test_embedded_json_in_text(self):
        result = _safe_parse_json('Some text {"type": "final", "message": "done"} more text')
        assert result == {"type": "final", "message": "done"}

    def test_embedded_array_in_text(self):
        result = _safe_parse_json('Explanation:\n[{"type": "plan"}]\nEnd.')
        assert result == [{"type": "plan"}]

    def test_empty_content(self):
        assert _safe_parse_json("") is None
        assert _safe_parse_json("   ") is None

    def test_non_json_text(self):
        assert _safe_parse_json("Just some random text without JSON") is None

    def test_nested_json_extraction(self):
        content = 'I think {"type": "read_file", "payload": {"path": "src/main.py"}} is the right action'
        result = _safe_parse_json(content)
        assert result == {"type": "read_file", "payload": {"path": "src/main.py"}}

    def test_json_with_escaped_chars(self):
        result = _safe_parse_json('{"message": "line1\\nline2"}')
        assert result == {"message": "line1\nline2"}


def _make_mock_registry():
    registry = MagicMock()
    registry.agents = {
        "supervisor": MagicMock(role="Supervisor", prompt="You are the supervisor", model_profile=None),
        "developer": MagicMock(role="Developer", prompt="You are the developer", model_profile=None),
        "tester": MagicMock(role="Tester", prompt="You are the tester", model_profile=None),
    }
    for name, agent in registry.agents.items():
        agent.description = f"Role: {agent.role}"
        agent.tools = ["read_file", "write_file", "run_shell"]
    return registry


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_multi_agent_orchestrator_success(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096

    orchestrator = MultiAgentOrchestrator(coding_loop)

    orchestrator._call_planner = AsyncMock(return_value=[{"action_type": "plan", "message": "Go!"}])
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": ["f1.py"]}
    ))
    orchestrator._call_reviewer = AsyncMock(return_value={"status": "approved", "feedback": "Good"})

    result = await orchestrator.run_planner_coder_reviewer("Task X")

    assert result.success is True
    assert orchestrator._call_planner.called
    assert coding_loop.run.called
    assert orchestrator._call_reviewer.called


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_multi_agent_orchestrator_revision(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096

    orchestrator = MultiAgentOrchestrator(coding_loop)

    orchestrator._call_planner = AsyncMock(return_value=[{"action_type": "plan", "message": "Go!"}])
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": ["f1.py"]}
    ))
    orchestrator._call_reviewer = AsyncMock(side_effect=[
        {"status": "rejected", "feedback": "Fix Y"},
        {"status": "approved", "feedback": "Fixed"}
    ])

    result = await orchestrator.run_planner_coder_reviewer("Task X")

    assert result.success is True
    assert orchestrator._call_planner.call_count == 2
    assert coding_loop.run.call_count == 2
    assert orchestrator._call_reviewer.call_count == 2


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_multi_agent_blackboard_and_routing(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096
    coding_loop.agent_client = MagicMock()

    orchestrator = MultiAgentOrchestrator(coding_loop)

    assert orchestrator.router is not None

    orchestrator.router.chat_completion_with_fallback = AsyncMock(side_effect=[
        {"choices": [{"message": {"content": '[{"type": "write_file", "path": "x.txt", "content": "hello"}]'}}]},
        {"choices": [{"message": {"content": '{"status": "rejected", "feedback": "please fix x"}'}}]},
        {"choices": [{"message": {"content": '[{"type": "write_file", "path": "x.txt", "content": "hello fixed"}]'}}]},
        {"choices": [{"message": {"content": '{"status": "approved", "feedback": "approved!"}'}}]},
    ])

    mock_events = []
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True,
        message="Done",
        metrics={"changed_files": ["x.txt"]},
        events=mock_events
    ))

    result = await orchestrator.run_planner_coder_reviewer("Task X", max_iterations=2)

    assert result.success is True
    dialog_event = next(e for e in result.events if e.get("event") == "multi_agent.dialog")
    assert dialog_event is not None
    messages = dialog_event["messages"]

    senders = {m["sender"] for m in messages}
    assert "Planner" in senders
    assert "Coder" in senders
    assert "Reviewer" in senders

    assert any("x.txt" in m["content"] or "x.txt" in str(m["metadata"]) for m in messages)


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_supervisor_cycle_detection(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096
    coding_loop.config.agent_registry_file = "config/agent-registry.yaml"
    coding_loop.current_agent = None

    orchestrator = MultiAgentOrchestrator(coding_loop)

    async def _always_developer(*args, **kwargs):
        return {"next_agent": "developer", "instruction": "keep working", "type": "action"}

    orchestrator._call_supervisor = _always_developer
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": []}
    ))

    result = await orchestrator.run_supervisor("Test task", max_steps=10)

    assert result.success is False
    assert "cycle" in result.error.lower() or "stuck" in result.error.lower()


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_supervisor_invalid_decision_fallback(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096
    coding_loop.config.agent_registry_file = "config/agent-registry.yaml"
    coding_loop.current_agent = None

    orchestrator = MultiAgentOrchestrator(coding_loop)

    async def _always_none(*args, **kwargs):
        return None

    orchestrator._call_supervisor = _always_none
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": []}
    ))

    result = await orchestrator.run_supervisor("Test task", max_steps=2)
    assert result is not None


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_supervisor_subtask_status_update(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096
    coding_loop.config.agent_registry_file = "config/agent-registry.yaml"
    coding_loop.current_agent = None

    orchestrator = MultiAgentOrchestrator(coding_loop)

    call_count = 0

    async def _supervisor_decision(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "sub_tasks": [
                    {"id": "task1", "description": "Do something", "status": "in_progress", "assigned_to": "developer"}
                ],
                "next_agent": "developer",
                "instruction": "Do the thing",
                "type": "action",
            }
        return {"type": "final", "message": "All done", "next_agent": "final"}

    orchestrator._call_supervisor = _supervisor_decision
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Completed task", metrics={"changed_files": ["output.txt"]}
    ))

    result = await orchestrator.run_supervisor("Test task", max_steps=5)

    assert result.success is True

    events = result.events or []
    dialog = [e for e in events if e.get("event") == "multi_agent.dialog"]
    assert len(dialog) > 0


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_planner_empty_plan_fallback(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096

    orchestrator = MultiAgentOrchestrator(coding_loop)

    # Planner returns empty list -> fallback to default plan
    orchestrator._call_planner = AsyncMock(return_value=[])
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": []}
    ))
    orchestrator._call_reviewer = AsyncMock(return_value={"status": "approved", "feedback": "ok"})

    result = await orchestrator.run_planner_coder_reviewer("Task X", max_iterations=1)
    assert result.success is True


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_reviewer_invalid_response_fallback(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096

    orchestrator = MultiAgentOrchestrator(coding_loop)

    orchestrator._call_planner = AsyncMock(return_value=[{"type": "plan", "message": "Go!"}])
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": []}
    ))
    # Reviewer returns None (invalid) -> orchestrator should continue with retry
    orchestrator._call_reviewer = AsyncMock(side_effect=[
        None,
        {"status": "approved", "feedback": "ok"},
    ])

    result = await orchestrator.run_planner_coder_reviewer("Task X", max_iterations=2)
    assert result.success is True


@pytest.mark.asyncio
@patch("scripts.llm_harness.mas.registry.AgentRegistry.load")
async def test_supervisor_enriches_blackboard(mock_load):
    mock_load.return_value = _make_mock_registry()
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    coding_loop.config = MagicMock()
    coding_loop.config.max_tokens = 4096
    coding_loop.config.agent_registry_file = "config/agent-registry.yaml"
    coding_loop.current_agent = None

    orchestrator = MultiAgentOrchestrator(coding_loop)

    call_count = 0

    async def _supervisor_decider(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"next_agent": "developer", "instruction": "Write test file", "type": "action"}
        return {"type": "final", "message": "Done", "next_agent": "final"}

    orchestrator._call_supervisor = _supervisor_decider
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="File written", metrics={"changed_files": ["test.txt"]}
    ))

    result = await orchestrator.run_supervisor("Test enrichment", max_steps=5)

    assert result.success is True
    events = result.events or []
    dialog = [e for e in events if e.get("event") == "multi_agent.dialog"]
    assert len(dialog) > 0

    messages = dialog[0]["messages"]
    developer_msgs = [m for m in messages if m["sender"] == "developer"]
    assert len(developer_msgs) > 0
    assert developer_msgs[-1]["metadata"].get("changed_files") == ["test.txt"]
    assert developer_msgs[-1]["metadata"].get("success") is True
