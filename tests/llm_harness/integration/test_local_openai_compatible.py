import os
import json
from typing import cast

import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.providers import LocalOpenAICompatibleProvider
from scripts.llm_harness.workspace import Workspace

# Environment variables for local LLM integration tests
RUN_LOCAL = os.environ.get("LLM_HARNESS_RUN_LOCAL_LLM_TESTS") == "1"
BASE_URL = os.environ.get("LLM_HARNESS_LOCAL_BASE_URL")
MODEL = os.environ.get("LLM_HARNESS_LOCAL_MODEL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.local_llm,
    pytest.mark.skipif(not RUN_LOCAL, reason="LLM_HARNESS_RUN_LOCAL_LLM_TESTS not set to 1"),
    pytest.mark.skipif(not BASE_URL or not MODEL, reason="LLM_HARNESS_LOCAL_BASE_URL or LLM_HARNESS_LOCAL_MODEL not set")
]

@pytest.fixture
def agent_client():
    assert BASE_URL is not None
    assert MODEL is not None
    return AgentClient(
        agent_id="test-local-integration",
        provider="local-openai-compatible",
        base_url=cast(str, BASE_URL),
        model=cast(str, MODEL),
        api_key_env="LLM_HARNESS_LOCAL_API_KEY"
    )

@pytest.mark.asyncio
async def test_local_llm_health(agent_client):
    """Test health check against local LLM provider."""
    assert BASE_URL is not None
    assert MODEL is not None
    provider = LocalOpenAICompatibleProvider(
        {
            "agent_id": "test-local-integration",
            "provider": "local-openai-compatible",
            "base_url": cast(str, BASE_URL),
            "model": cast(str, MODEL),
            "api_key_env": "LLM_HARNESS_LOCAL_API_KEY",
        }
    )
    health = await provider.health_check()
    assert health["status"] == "healthy"
    assert health["details"]

@pytest.mark.asyncio
async def test_local_llm_simple_chat(agent_client):
    """Test simple chat completion with local LLM."""
    messages = [
        {"role": "user", "content": 'Say hello and return a valid JSON: {"type": "final", "reason": "greeting", "payload": {"message": "hello"}}'}
    ]
    response = await agent_client.chat_completion(messages)
    assert "choices" in response
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert content["message"] == "hello"

@pytest.mark.asyncio
async def test_local_llm_coding_loop_minimal(agent_client, tmp_path):
    """Test a minimal CodingLoop execution with real local LLM."""
    # Setup a minimal repo
    app_file = tmp_path / "hello.py"
    app_file.write_text("def greet():\n    return 'hi'\n")
    
    async with Workspace(base_path=str(tmp_path)) as ws:
        loop = CodingLoop(
            agent_client=agent_client,
            workspace=ws,
            max_steps=3
        )
        
        # We ask for a very simple task that can be finished in one step
        task = "Read hello.py and then finish with a 'final' action saying you are done."
        result = await loop.run(task=task)
        
        # Validate that we got a result and at least one step was executed
        assert result is not None
        assert len(result.events) > 0
        # The agent should eventually emit a 'final' action if it's capable
        has_final = any(e.get("action_type") == "final" for e in result.events if e.get("event") == "action.completed")
        assert has_final, "Agent failed to complete the task with a 'final' action"


@pytest.mark.asyncio
async def test_local_llm_coding_loop_native_stream_write_then_final(tmp_path):
    """Exercise the LM Studio-style native tool path with streaming enabled."""
    assert BASE_URL is not None
    assert MODEL is not None
    client = AgentClient(
        agent_id="test-local-native-stream",
        provider="local-openai-compatible",
        base_url=cast(str, BASE_URL),
        model=cast(str, MODEL),
        api_key_env="LLM_HARNESS_LOCAL_API_KEY",
        local_model_timeout=300.0,
        auto_increase_timeout=True,
        stream=True,
        tool_calling="auto",
    )

    async with Workspace(base_path=str(tmp_path)) as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=4, timeout=300)
        result = await loop.run(
            task=(
                "Create a file named SMOKE_TEST_NATIVE.md containing exactly: "
                "LM Studio native smoke test passed."
            )
        )

        assert result.success is True
        assert ws.read_file("SMOKE_TEST_NATIVE.md") == "LM Studio native smoke test passed."
        assert result.metrics.get("final_executed") is True
        assert result.metrics.get("post_final_llm_calls_blocked", 0) == 0
        assert result.metrics.get("time_to_first_action_ms") is not None
        assert result.metrics.get("time_to_final_ms") is not None


@pytest.mark.asyncio
async def test_local_llm_coding_loop_json_no_stream_write_then_final(tmp_path):
    """Exercise the LM Studio-style JSON multi-turn path without streaming."""
    assert BASE_URL is not None
    assert MODEL is not None
    client = AgentClient(
        agent_id="test-local-json-no-stream",
        provider="local-openai-compatible",
        base_url=cast(str, BASE_URL),
        model=cast(str, MODEL),
        api_key_env="LLM_HARNESS_LOCAL_API_KEY",
        local_model_timeout=300.0,
        auto_increase_timeout=True,
        stream=False,
        tool_calling="json",
    )

    async with Workspace(base_path=str(tmp_path)) as ws:
        loop = CodingLoop(agent_client=client, workspace=ws, max_steps=4, timeout=300)
        result = await loop.run(
            task=(
                "Create a file named SMOKE_TEST_JSON.md containing exactly: "
                "LM Studio json smoke test passed."
            )
        )

        assert result.success is True
        assert ws.read_file("SMOKE_TEST_JSON.md") == "LM Studio json smoke test passed."
        assert result.metrics.get("final_executed") is True
        assert result.metrics.get("post_final_llm_calls_blocked", 0) == 0
