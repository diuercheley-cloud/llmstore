import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.providers import create_code_agent

LMSTUDIO_BASE_URL = "http://192.168.101.1:1234/v1"
NEMOTRON_MODEL = "nvidia/nemotron-3-nano-4b"


def _lmstudio_config(**overrides):
    base = {
        "agent_id": "lmstudio-test",
        "base_url": LMSTUDIO_BASE_URL,
        "model": NEMOTRON_MODEL,
        "stream": False,
    }
    base.update(overrides)
    return base


class TestLMStudioHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_reports_healthy(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        health = await agent.health_check()
        assert health["status"] == "healthy"
        assert health["provider"] == "local-openai-compatible"
        assert NEMOTRON_MODEL in health["details"]["available_models"]
        assert health["details"]["selected_model"] == NEMOTRON_MODEL
        assert health["details"]["auto_selected_model"] is False

    @pytest.mark.asyncio
    async def test_health_check_no_api_key_required(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(api_key_env="NONEXISTENT_KEY"),
        )
        health = await agent.health_check()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_response_format_not_supported(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        health = await agent.health_check()
        assert health["details"]["supports_response_format"] is False

    @pytest.mark.asyncio
    async def test_health_check_lists_models(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        health = await agent.health_check()
        models = health["details"]["available_models"]
        assert isinstance(models, list)
        assert len(models) >= 1


class TestLMStudioPlainChat:
    @pytest.mark.asyncio
    async def test_plain_chat_returns_response(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(plain_chat=True),
        )
        result = await agent.chat_completion([{"role": "user", "content": "Say hello"}])
        assert "choices" in result
        content = result["choices"][0]["message"]["content"]
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_plain_chat_no_action_validation(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(plain_chat=True),
        )
        result = await agent.chat_completion([{"role": "user", "content": "What is 2+2?"}])
        content = result["choices"][0]["message"]["content"]
        assert "4" in content

    @pytest.mark.asyncio
    async def test_plain_chat_returns_reasoning_content(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(plain_chat=True),
        )
        result = await agent.chat_completion([{"role": "user", "content": "Count r in strawberry"}])
        msg = result["choices"][0]["message"]
        assert "reasoning_content" in msg

    @pytest.mark.asyncio
    async def test_plain_chat_temperature_zero(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(plain_chat=True),
        )
        post_payloads = []

        async def capture(method, url, **kwargs):
            if method == "GET":
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"data": [{"id": NEMOTRON_MODEL}]}
                return mock_resp
            post_payloads.append(kwargs.get("json", {}))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"total_tokens": 5},
            }
            return mock_resp

        with patch("scripts.llm_harness.providers.httpx.AsyncClient") as cls:
            mock_client = AsyncMock()
            mock_client.request = capture
            cls.return_value.__aenter__.return_value = mock_client
            await agent.chat_completion([{"role": "user", "content": "hi"}])

        assert post_payloads[0].get("temperature") == 0


class TestLMStudioCodingAgent:
    @pytest.mark.asyncio
    async def test_coding_agent_returns_action_json(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        result = await agent.chat_completion(
            [{"role": "user", "content": "List files in current directory"}]
        )
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        assert "type" in parsed or "action_type" in parsed

    @pytest.mark.asyncio
    async def test_coding_agent_action_type_alias(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        result = await agent.chat_completion(
            [{"role": "user", "content": "List files in current directory"}]
        )
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        action_type = parsed.get("type") or parsed.get("action_type")
        assert action_type in {
            "plan",
            "read_file",
            "write_file",
            "list_files",
            "run_shell",
            "run_tests",
            "grep",
            "final",
        }

    @pytest.mark.asyncio
    async def test_coding_agent_returns_valid_usage(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        result = await agent.chat_completion([{"role": "user", "content": "echo hello"}])
        usage = result.get("usage", {})
        assert "total_tokens" in usage
        assert usage["total_tokens"] >= 0


class TestLMStudioModelResolution:
    @pytest.mark.asyncio
    async def test_explicit_model_selected(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        assert agent.model == NEMOTRON_MODEL

    @pytest.mark.asyncio
    async def test_auto_selects_first_model(self):
        agent = create_code_agent(
            "local-openai-compatible",
            {
                "agent_id": "test",
                "base_url": LMSTUDIO_BASE_URL,
                "stream": False,
            },
        )
        await agent.chat_completion([{"role": "user", "content": "hi"}])
        assert agent.model != ""

    @pytest.mark.asyncio
    async def test_wrong_model_suggests_alternatives(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(model="nonexistent-model-xyz"),
        )
        with pytest.raises(ValueError, match="was not found"):
            await agent.chat_completion([{"role": "user", "content": "hi"}])


class TestLMStudioToolCalling:
    @pytest.mark.asyncio
    async def test_probe_native_tool_calling_result(self):
        agent = create_code_agent("local-openai-compatible", _lmstudio_config())
        probe = await agent._probe_native_tool_calling()
        assert "supported" in probe
        assert isinstance(probe["supported"], bool)

    @pytest.mark.asyncio
    async def test_tool_calling_mode_defaults_to_json(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(tool_calling="auto"),
        )
        mode = await agent.resolve_tool_calling_mode()
        assert mode in ("json", "native")

    @pytest.mark.asyncio
    async def test_json_tool_mode_no_tools_in_payload(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(tool_calling="json"),
        )
        sent = []

        async def capture(method, url, **kwargs):
            sent.append(kwargs.get("json", {}))
            if method == "GET":
                mock = MagicMock()
                mock.status_code = 200
                mock.json.return_value = {"data": [{"id": NEMOTRON_MODEL}]}
                return mock
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"type":"final","payload":{"message":"done"}}',
                        }
                    }
                ],
                "usage": {"total_tokens": 5},
            }
            return mock_resp

        with patch("scripts.llm_harness.providers.httpx.AsyncClient") as cls:
            mock_client = AsyncMock()
            mock_client.request = capture
            cls.return_value.__aenter__.return_value = mock_client
            await agent.chat_completion([{"role": "user", "content": "hi"}])

        assert "tools" not in sent[-1]


class TestLMStudioSSEParsing:
    @pytest.mark.asyncio
    async def test_sse_multiline_events(self):
        agent = create_code_agent(
            "local-openai-compatible",
            _lmstudio_config(base_url="http://localhost:1234/v1"),
        )

        class FakeResponse:
            async def aiter_lines(self):
                for line in [
                    'data: {"choices":[{"delta":{"content":"hel"}}]}',
                    "",
                    'data: {"choices":[{"delta":{"content":"lo"}}]}',
                    "",
                    "data: [DONE]",
                    "",
                ]:
                    yield line

        events = []
        async for item in agent._iter_sse_data(FakeResponse()):
            events.append(item)
        assert len(events) == 3
        assert events[0] == '{"choices":[{"delta":{"content":"hel"}}]}'
        assert events[1] == '{"choices":[{"delta":{"content":"lo"}}]}'
        assert events[2] == "[DONE]"
