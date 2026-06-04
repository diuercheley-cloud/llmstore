import os
import subprocess
import sys
from typing import cast

import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.completions import CompletionRequest, get_completion_suggestions
from scripts.llm_harness.ide.inline_edit import perform_inline_edit
from scripts.llm_harness.ide.models import InlineEditRequest
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.providers import LocalOpenAICompatibleProvider
from scripts.llm_harness.workspace import Workspace

# Environment variables for local LLM integration tests
RUN_LOCAL = os.environ.get("LLM_HARNESS_RUN_LOCAL_LLM_TESTS") == "1"
BASE_URL = os.environ.get("LLM_HARNESS_LOCAL_BASE_URL")
MODEL = os.environ.get("LLM_HARNESS_LOCAL_MODEL")
RUN_NATIVE = os.environ.get("LLM_HARNESS_RUN_LOCAL_NATIVE_TOOL_TESTS") == "1"

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


def _local_provider_config(**overrides):
    assert BASE_URL is not None
    assert MODEL is not None
    config = {
        "agent_id": "test-local-integration",
        "provider": "local-openai-compatible",
        "base_url": cast(str, BASE_URL),
        "model": cast(str, MODEL),
        "api_key_env": "LLM_HARNESS_LOCAL_API_KEY",
        "plain_chat": True,
        "local_model_timeout": 300.0,
        "auto_increase_timeout": True,
        "stream": False,
        "max_tokens": 256,
    }
    config.update(overrides)
    return config

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
    """Test simple plain chat completion with local LLM."""
    provider = LocalOpenAICompatibleProvider(_local_provider_config())
    messages = [{"role": "user", "content": "Say exactly READY"}]
    response = await provider.chat_completion(messages)
    assert "choices" in response
    content = response["choices"][0]["message"]["content"].strip()
    assert "READY" in content


@pytest.mark.asyncio
async def test_local_llm_completion_smoke(tmp_path):
    """Exercise local plain-chat completions against a real OpenAI-compatible endpoint."""
    app_file = tmp_path / "sample.py"
    app_file.write_text("def answer():\n    return \n")

    request = CompletionRequest(
        file_path="sample.py",
        cursor_line=2,
        cursor_column=11,
    )
    suggestions = await get_completion_suggestions(
        request=request,
        workspace_root=str(tmp_path),
        provider_name="local-openai-compatible",
        config_overrides=_local_provider_config(max_tokens=128),
    )

    assert suggestions
    assert suggestions[0].text.strip()
    assert "```" not in suggestions[0].text


@pytest.mark.asyncio
async def test_local_llm_inline_edit_smoke(tmp_path):
    """Exercise inline edit against the real local model using a deterministic replacement."""
    app_file = tmp_path / "calc.py"
    app_file.write_text("def add(a, b):\n    return a - b\n")

    provider = LocalOpenAICompatibleProvider(_local_provider_config(max_tokens=160))
    policy_engine = PolicyEngine()

    async with Workspace(base_path=str(tmp_path)) as workspace:
        request = InlineEditRequest(
            file_path="calc.py",
            start_line=2,
            end_line=2,
            instruction="Replace the target line with exactly:     return a + b",
        )
        result = await perform_inline_edit(
            request=request,
            provider=provider,
            policy_engine=policy_engine,
            workspace=workspace,
            dry_run=False,
        )

        assert result["success"] is True
        assert "return a + b" in workspace.read_file("calc.py")

@pytest.mark.asyncio
async def test_local_llm_coding_loop_minimal(tmp_path):
    """Test the supported CLI coding path against a real local LLM."""
    # Setup a minimal repo
    app_file = tmp_path / "hello.py"
    app_file.write_text("def greet():\n    return 'hi'\n")
    cmd = [
        sys.executable,
        "-m",
        "scripts.llm_harness.cli",
        "code",
        "--provider",
        "local-openai-compatible",
        "--base-url",
        cast(str, BASE_URL),
        "--model",
        cast(str, MODEL),
        "--tool-calling",
        "json",
        "--no-stream",
        "--loop-timeout",
        "90",
        "--local-model-timeout",
        "45",
        "--workspace",
        str(tmp_path),
        "--task",
        "Read hello.py and then finish with a final action saying READY",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), check=False)

    assert result.returncode == 0, result.stderr or result.stdout
    assert "SUCCESS:" in result.stdout


@pytest.mark.asyncio
@pytest.mark.skipif(
    not RUN_NATIVE,
    reason="LLM_HARNESS_RUN_LOCAL_NATIVE_TOOL_TESTS not set to 1",
)
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
async def test_local_llm_code_auto_json_smoke(tmp_path):
    """Exercise the supported auto mode CLI path against the local model."""
    app_file = tmp_path / "hello.py"
    app_file.write_text("def greet():\n    return 'hi'\n")
    cmd = [
        sys.executable,
        "-m",
        "scripts.llm_harness.cli",
        "code",
        "--provider",
        "local-openai-compatible",
        "--base-url",
        cast(str, BASE_URL),
        "--model",
        cast(str, MODEL),
        "--tool-calling",
        "json",
        "--no-stream",
        "--loop-timeout",
        "90",
        "--local-model-timeout",
        "45",
        "--auto",
        "--max-auto-fixes",
        "2",
        "--workspace",
        str(tmp_path),
        "--task",
        "Read hello.py and then finish with a final action saying AUTO_READY",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), check=False)

    assert result.returncode == 0, result.stderr or result.stdout
    assert "SUCCESS:" in result.stdout
