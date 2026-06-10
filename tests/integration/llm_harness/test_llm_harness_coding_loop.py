import os
from unittest.mock import AsyncMock, patch

import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.models import PatchResult
from scripts.llm_harness.tools.shell import ShellResult
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_coding_loop_timeout():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, timeout=0)
        result = await loop.run(task="Fix bug")
        assert result.success is False
        assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_coding_loop_success_simulated_emits_run_completed():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(task="Fix this bug")
        assert result.success is True
        assert "simulated" in result.message
        assert [event["event"] for event in result.events] == [
            "run.started",
            "context.managed",
            "action.started",
            "action.completed",
            "run.completed",
        ]
        assert result.events[-1]["event"] == "run.completed"


@pytest.mark.asyncio
async def test_coding_loop_short_circuit_enabled():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, allow_test_short_circuit=True)
        loop.provider = "stub"
        with patch.object(
            client,
            "chat_completion",
            AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "not json content",
                            }
                        }
                    ]
                }
            ),
        ) as mock_chat:
            result = await loop.run(task="Fix this bug")
            assert result.success is True
            assert "simulated" in result.message
            mock_chat.assert_called_once()


@pytest.mark.asyncio
async def test_coding_loop_short_circuit_disabled_by_default():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        loop.provider = "stub"
        with patch.object(
            client,
            "chat_completion",
            AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "not json content",
                            }
                        }
                    ]
                }
            ),
        ) as mock_chat:
            result = await loop.run(task="Fix this bug")
            assert result.success is False
            assert "unparseable" in result.error.lower()
            mock_chat.assert_called_once()



@pytest.mark.asyncio
async def test_coding_loop_emits_complete_subaction_sequence():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        ws.write_file("hello.txt", "hello")
        loop = CodingLoop(agent_client=client, workspace=ws)

        with patch.object(loop.test_tools, "run_pytest", AsyncMock(return_value={"success": True, "exit_code": 0, "output": "ok", "error": ""})), patch.object(
            loop.patcher,
            "apply_patch",
            return_value=PatchResult(success=True, mode="apply"),
        ):
            result = await loop.run(
                task="Implement change",
                action_plan=[
                    {"action_type": "plan", "message": "Planning steps"},
                    {"action_type": "apply_patch", "diff": "--- a/hello.txt\n+++ b/hello.txt\n@@ -1 +1 @@\n-hello\n+hello world"},
                    {"action_type": "run_tests", "test_path": "tests/"},
                    {"action_type": "final", "message": "done"},
                ],
            )

        assert result.success is True
        assert [event["event"] for event in result.events] == [
            "run.started",
            "context.managed",
            "action.started",
            "action.completed",
            "action.started",
            "action.completed",
            "action.started",
            "action.completed",
            "action.started",
            "action.completed",
            "run.completed",
        ]
        assert [event["action_type"] for event in result.events] == [
            "loop",
            "context",
            "plan",
            "plan",
            "apply_patch",
            "apply_patch",
            "run_tests",
            "run_tests",
            "final",
            "final",
            "loop",
        ]
        assert [event["step"] for event in result.events] == sorted(event["step"] for event in result.events)


@pytest.mark.asyncio
async def test_coding_loop_emits_action_failed_when_tool_fails():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        with patch.object(loop.test_tools, "run_pytest", AsyncMock(return_value={"success": False, "exit_code": 1, "output": "Authorization: Bearer abc", "error": "api_key=sk-fail"})):
            result = await loop.run(
                task="Run tests",
                action_plan=[{"action_type": "run_tests", "test_path": "tests/"}],
            )

        assert result.success is False
        failed = [event for event in result.events if event["event"] == "action.failed"]
        assert failed
        assert failed[0]["action_type"] == "run_tests"
        assert "abc" not in failed[0]["message"]
        assert "sk-fail" not in failed[0]["message"]


@pytest.mark.asyncio
async def test_coding_loop_emits_policy_blocked_for_denied_command():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(
            task="Run blocked command",
            action_plan=[{"action_type": "run_shell", "command": "ls; rm -rf /"}],
        )

        assert result.success is False
        blocked = [event for event in result.events if event["event"] == "policy.blocked"]
        assert blocked
        assert blocked[0]["action_type"] == "run_shell"
        assert blocked[0]["status"] == "blocked"


@pytest.mark.asyncio
async def test_coding_loop_sanitizes_event_messages():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        with patch.object(loop.test_tools, "run_pytest", AsyncMock(return_value={"success": False, "exit_code": 1, "output": "Bearer token-123", "error": "Authorization: Bearer token-123 api_key=sk-secret"})):
            result = await loop.run(
                task="Run tests",
                action_plan=[{"action_type": "run_tests", "test_path": "tests/"}],
            )

        serialized = str(result.events)
        assert "token-123" not in serialized
        assert "sk-secret" not in serialized
        assert "[REDACTED]" in serialized


@pytest.mark.asyncio
async def test_coding_loop_executes_agent_json_actions():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"actions":[{"action_type":"run_shell","command":"echo ok"}],'
                            '"final":"done"}'
                        ),
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(task="Implement change")

    assert result.success is True
    assert result.message == "done"
    assert [event["action_type"] for event in result.events] == [
        "loop",
        "context",
        "run_shell",
        "run_shell",
        "final",
        "final",
        "loop",
    ]


@pytest.mark.asyncio
async def test_coding_loop_stops_when_final_action_executes_without_explicit_final_field():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final"}',
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=3)
        result = await loop.run(task="Finish immediately")

    assert result.success is True
    assert result.message == "Loop finished"
    assert client.chat_completion.await_count == 1
    assert result.events[-1]["event"] == "run.completed"


@pytest.mark.asyncio
async def test_coding_loop_executes_native_tool_call_write_file():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "write_file",
                                        "arguments": '{"path":"note.txt","content":"hello"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"final","message":"done"}',
                        }
                    }
                ]
            },
        ]
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=3)
        result = await loop.run(task="Create note.txt and finish")
        assert result.success is True
        assert ws.read_file("note.txt") == "hello"
        assert client.chat_completion.await_count == 2


@pytest.mark.asyncio
async def test_coding_loop_stops_after_native_final_tool_call():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "final",
                                    "arguments": '{"message":"done"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=3)
        result = await loop.run(task="Finish immediately")
    assert result.success is True
    assert result.message == "done"
    assert client.chat_completion.await_count == 1


@pytest.mark.asyncio
async def test_coding_loop_stops_executing_actions_after_final():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(
            task="Finish immediately",
            action_plan=[
                {"action_type": "write_file", "path": "before.txt", "content": "ok"},
                {"action_type": "final", "message": "done"},
                {"action_type": "write_file", "path": "after.txt", "content": "should-not-run"},
            ],
        )
        assert ws.read_file("before.txt") == "ok"
        assert not os.path.exists(ws.get_path("after.txt"))

    assert result.success is True
    assert result.message == "done"
    assert result.metrics["final_executed"] is True
    assert result.metrics["time_to_first_action_ms"] is not None
    assert result.metrics["time_to_final_ms"] is not None


@pytest.mark.asyncio
async def test_coding_loop_stops_executing_native_tool_calls_after_final():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "final",
                                    "arguments": '{"message":"done"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": '{"path":"after.txt","content":"should-not-run"}',
                                },
                            },
                        ],
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=3)
        result = await loop.run(task="Finish immediately")
        assert not os.path.exists(ws.get_path("after.txt"))

    assert result.success is True
    assert result.message == "done"
    assert client.chat_completion.await_count == 1


@pytest.mark.asyncio
async def test_coding_loop_native_tool_call_policy_block_remains_blocked():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "run_shell",
                                    "arguments": '{"command":"rm -rf /","timeout":1}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=1)
        result = await loop.run(task="Do something dangerous")
        assert result.success is False
        assert any(event["event"] == "policy.blocked" for event in result.events)


@pytest.mark.asyncio
async def test_coding_loop_parser_accepts_text_before_json():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": 'Here is the result:\n{"action_type":"final","message":"done"}\nThanks.',
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(task="Finish")
        assert result.success is True


@pytest.mark.asyncio
async def test_coding_loop_parser_accepts_markdown_json_block():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '```json\n{"action_type":"final","message":"done"}\n```',
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(task="Finish")
        assert result.success is True


@pytest.mark.asyncio
async def test_coding_loop_parser_rejects_partial_json():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final","message":"done"',
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(task="Finish")
        assert result.success is False
        assert "unparseable" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_coding_loop_executes_mocked_real_sequence():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            {"choices": [{"message": {"role": "assistant", "content": '{"action_type":"plan","message":"Planning"}'}}]},
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"apply_patch","diff":"--- a/hello.txt\\n+++ b/hello.txt\\n@@ -1 +1 @@\\n-hello\\n+hello world"}',
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"run_tests","test_path":"tests/"}',
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"final","message":"done"}',
                        }
                    }
                ]
            },
        ]
    )
    async with Workspace() as ws:
        ws.write_file("hello.txt", "hello")
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=4)
        with patch.object(
            loop.test_tools,
            "run_pytest",
            AsyncMock(return_value={"success": True, "exit_code": 0, "output": "ok", "error": ""}),
        ), patch.object(
            loop.patcher,
            "apply_patch",
            return_value=PatchResult(success=True, mode="apply"),
        ):
            result = await loop.run(task="Implement change")

    assert result.success is True
    assert result.message == "done"
    assert [event["action_type"] for event in result.events] == [
        "loop",
        "context",
        "plan",
        "plan",
        "context",
        "apply_patch",
        "apply_patch",
        "context",
        "run_tests",
        "run_tests",
        "context",
        "final",
        "final",
        "loop",
    ]


@pytest.mark.asyncio
async def test_trace_hash_changes_when_output_changes():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        with patch.object(
            loop.shell_tools,
            "run_shell_async",
            AsyncMock(return_value=ShellResult(output="first", returncode=0)),
        ):
            first = await loop.run(
                task="Run command",
                action_plan=[{"action_type": "run_shell", "command": "echo first"}, {"action_type": "final", "message": "done"}],
            )

        loop2 = CodingLoop(agent_client=client, workspace=ws)
        with patch.object(
            loop2.shell_tools,
            "run_shell_async",
            AsyncMock(return_value=ShellResult(output="second", returncode=0)),
        ):
            second = await loop2.run(
                task="Run command",
                action_plan=[{"action_type": "run_shell", "command": "echo second"}, {"action_type": "final", "message": "done"}],
            )

    assert first.trace_hash
    assert second.trace_hash
    assert first.trace_hash != second.trace_hash


@pytest.mark.asyncio
async def test_trace_sanitizes_secrets():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        with patch.object(
            loop.shell_tools,
            "run_shell_async",
            AsyncMock(
                return_value=ShellResult(
                    output="Authorization: Bearer token-123 api_key=sk-secret",
                    returncode=0,
                )
            ),
        ):
            result = await loop.run(
                task="Run command",
                action_plan=[{"action_type": "run_shell", "command": "echo secret"}, {"action_type": "final", "message": "done"}],
            )

    serialized = str(result.trace)
    assert "token-123" not in serialized
    assert "sk-secret" not in serialized
    assert "[REDACTED]" in serialized


@pytest.mark.asyncio
async def test_coding_loop_sends_prompt_builder_output():
    """CodingLoop must send PromptBuilder-generated system prompt to the provider."""
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final","message":"done"}',
                    }
                }
            ]
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=1)
        await loop.run(task="Test prompt")

    # The history sent to chat_completion must include the PromptBuilder system prompt
    assert client.chat_completion.call_args is not None
    history = client.chat_completion.call_args[0][0]

    system_msgs = [m for m in history if m.get("role") == "system"]
    assert system_msgs, "No system message in history"
    system_content = system_msgs[0]["content"]
    assert "Senior Software Engineer AI Agent" in system_content
    assert "Guidelines" in system_content

    user_msgs = [m for m in history if m.get("role") == "user"]
    assert user_msgs, "No user message in history"
    user_content = user_msgs[0]["content"]
    assert "Test prompt" in user_content
    assert "Respond only with the next action as a JSON object" in user_content


@pytest.mark.asyncio
async def test_coding_loop_accumulates_token_metrics():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final","message":"done"}',
                    }
                }
            ],
            "usage": {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=1)
        loop.provider = "openai-compatible"
        loop.model = "gpt-4"
        result = await loop.run(task="Test tokens")

    assert result.llm_calls == 1
    assert result.total_tokens == 50
    assert result.prompt_tokens == 20
    assert result.completion_tokens == 30
    assert result.llm_provider == "openai-compatible"
    assert result.llm_model == "gpt-4"


@pytest.mark.asyncio
async def test_coding_loop_accumulates_multiple_calls():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"plan","message":"Planning"}',
                        }
                    }
                ],
                "usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action_type":"final","message":"done"}',
                        }
                    }
                ],
                "usage": {"total_tokens": 20, "prompt_tokens": 10, "completion_tokens": 10},
            },
        ]
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=2)
        loop.provider = "openai-compatible"
        result = await loop.run(task="Test multi-call tokens")

    assert result.llm_calls == 2
    assert result.total_tokens == 30
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 15


@pytest.mark.asyncio
async def test_coding_loop_no_usage_defaults_to_zero():
    client = AgentClient(agent_id="test")
    client.chat_completion = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final","message":"done"}',
                    }
                }
            ],
        }
    )
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=1)
        result = await loop.run(task="Test no usage")

    assert result.llm_calls == 1
    assert result.total_tokens == 0
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0


@pytest.mark.asyncio
async def test_coding_loop_blocks_sensitive_file_reads():
    client = AgentClient(agent_id="test")
    async with Workspace() as ws:
        loop = CodingLoop(agent_client=client, workspace=ws)
        result = await loop.run(
            task="Read a file",
            action_plan=[{"action_type": "read_file", "path": ".env"}],
        )

    assert result.success is False
    blocked = [event for event in result.events if event["event"] == "policy.blocked"]
    assert blocked
    assert blocked[0]["action_type"] == "read_file"
