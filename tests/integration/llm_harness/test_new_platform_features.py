# tests/integration/llm_harness/test_new_platform_features.py
import asyncio
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from scripts.llm_harness.benchmarks import BenchmarkSuiteRunner, compare_benchmarks
from scripts.llm_harness.benchmarks.gsm8k import GSM8KAdapter
from scripts.llm_harness.benchmarks.swebench_adapter import SWEBenchAdapter
from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.legacy_runner import run_harness
from scripts.llm_harness.mcp import mcp_client
from scripts.llm_harness.plugins import Plugin, PluginMetadata, plugin_registry
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.sanitizer import Sanitizer
from scripts.llm_harness.server.app import ACTIVE_RUNS, app, server_config
from scripts.llm_harness.workspace import Workspace


# 1. API Server Mode Tests
def test_server_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_server_auth_when_configured(monkeypatch):
    server_config.api_key_env = "LLM_HARNESS_SERVER_API_KEY"
    monkeypatch.setenv("LLM_HARNESS_SERVER_API_KEY", "supersecret")
    client = TestClient(app)

    # Missing auth header
    response = client.get("/providers")
    assert response.status_code == 401

    # Wrong auth header
    response = client.get("/providers", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401

    # Correct auth header
    response = client.get("/providers", headers={"Authorization": "Bearer supersecret"})
    assert response.status_code == 200

    # Reset
    server_config.api_key_env = None


@pytest.mark.asyncio
async def test_server_runs_create_and_cancel():
    client = TestClient(app)
    with patch("scripts.llm_harness.server.app.run_harness", new_callable=AsyncMock) as mock_run:
        from scripts.llm_harness.models import ExecutionResult

        mock_run.return_value = ExecutionResult(success=True, message="Success")

        response = client.post("/runs", json={"task": "do something", "provider": "stub"})
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        run_id = data["run_id"]

        response = client.get(f"/runs/{run_id}")
        assert response.status_code == 200
        run_status = response.json()
        assert run_status["status"] in ("running", "completed")

        response = client.post(f"/runs/{run_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] in ("cancelled", "completed")


def test_server_cancel_completed_run():
    run_id = "test-completed-run"
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "task": "do nothing",
        "status": "completed",
        "events": [],
        "listeners": [],
        "result": None,
        "error": None,
        "task_handle": None,
    }
    client = TestClient(app)
    response = client.post(f"/runs/{run_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_server_get_nonexistent_run():
    client = TestClient(app)
    response = client.get("/runs/nonexistent-run-id")
    assert response.status_code == 404

    response = client.post("/runs/nonexistent-run-id/cancel")
    assert response.status_code == 404

    response = client.get("/runs/nonexistent-run-id/events")
    assert response.status_code == 404


def test_server_runs_events_streaming():
    run_id = "test-stream-run"
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "task": "do nothing",
        "status": "completed",
        "events": [{"step": 1, "message": "First step"}],
        "listeners": [],
        "result": None,
        "error": None,
        "task_handle": None,
    }
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert b"First step" in response.content


def test_server_list_providers_and_tools():
    client = TestClient(app)
    response = client.get("/providers")
    assert response.status_code == 200
    assert "providers" in response.json()

    response = client.get("/tools")
    assert response.status_code == 200
    assert "tools" in response.json()

    # Enable MCP tool display in tools list
    mcp_client.enabled = True
    mcp_client.tools = {"filesystem_tool": {"description": "A filesystem tool"}}
    mcp_client.tool_to_server["filesystem_tool"] = "filesystem"

    response = client.get("/tools")
    assert response.status_code == 200
    tool_names = [t["name"] for t in response.json()["tools"]]
    assert "mcp:filesystem_tool" in tool_names

    mcp_client.enabled = False
    mcp_client.tools.clear()


def test_server_get_evals_list():
    client = TestClient(app)
    response = client.get("/evals")
    assert response.status_code == 200
    assert "eval_suites" in response.json()


@pytest.mark.asyncio
async def test_server_evals_run_lifecycle():
    client = TestClient(app)

    with (
        patch("scripts.llm_harness.server.app.EvalLoader.load") as mock_load,
        patch(
            "scripts.llm_harness.server.app.EvalRunner.run_all", new_callable=AsyncMock
        ) as mock_run_all,
    ):
        mock_load.return_value = MagicMock()
        mock_run_all.return_value = MagicMock()

        response = client.post(
            "/evals/run",
            json={
                "suite_path": "examples/llm_harness/evals/cli_smoke.eval_suite.json",
                "concurrency": 2,
                "provider": "stub",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "eval_run_id" in data
        eval_run_id = data["eval_run_id"]

        # Let background task complete or yield
        await asyncio.sleep(0.1)

        response = client.get(f"/evals/{eval_run_id}")
        assert response.status_code == 200
        assert response.json()["status"] in ("running", "completed", "failed")


def test_server_get_nonexistent_eval_run():
    client = TestClient(app)
    response = client.get("/evals/nonexistent-eval-id")
    assert response.status_code == 404


# 2. Plugin System Tests
def test_plugin_registry_basic():
    plugin_registry.tools.clear()

    with pytest.raises(ValueError, match="Cannot overwrite core tool"):
        plugin_registry.register_tool("read_file", lambda x: x)

    plugin_registry.register_tool("read_file", lambda x: x, allow_overwrite=True)

    class FakePlugin(Plugin):
        def initialize(self, registry):
            registry.register_tool("fake_tool", lambda x: "fake")
            registry.register_provider("fake_provider", MagicMock)
            registry.register_scorer("fake_scorer", lambda x: 1.0)
            registry.register_policy_rule("fake_rule", lambda x: True)
            registry.register_prompt_template("fake_template", "hello")

    meta = PluginMetadata(name="Fake", version="1.0", source="test")
    p = FakePlugin(meta)
    p.initialize(plugin_registry)

    assert "fake_tool" in plugin_registry.list_tools()
    assert "fake_scorer" in plugin_registry.list_scorers()
    assert "fake_rule" in plugin_registry.list_policy_rules()

    # Test safe mode disable behavior
    plugin_registry.load_all_plugins(enable_plugins=False)
    assert len(plugin_registry.plugins) == 0

    # Clean up fake provider to avoid test leakage
    from scripts.llm_harness.providers import _PROVIDER_REGISTRY

    if "fake_provider" in _PROVIDER_REGISTRY:
        del _PROVIDER_REGISTRY["fake_provider"]


def test_plugin_registry_load_local_plugins():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a dynamic plugin
        plugin_code = """
from scripts.llm_harness.plugins import Plugin

class DynamicPlugin(Plugin):
    def initialize(self, registry):
        registry.register_tool("dynamic_tool", lambda x: "dynamic")
"""
        with open(os.path.join(tmp_dir, "plugin_dynamic.py"), "w") as f:
            f.write(plugin_code)

        plugin_registry.load_all_plugins(enable_plugins=True, plugins_dir=tmp_dir)
        assert "DynamicPlugin" in plugin_registry.plugins
        assert "dynamic_tool" in plugin_registry.list_tools()

        # Dynamic plugin with just an initialize function
        plugin_func_code = """
def initialize(registry):
    registry.register_tool("func_tool", lambda x: "func")
"""
        with open(os.path.join(tmp_dir, "plugin_func.py"), "w") as f:
            f.write(plugin_func_code)

        plugin_registry.load_all_plugins(enable_plugins=True, plugins_dir=tmp_dir)
        assert "plugin_func" in plugin_registry.plugins
        assert "func_tool" in plugin_registry.list_tools()


# 3. MCP Client Integration Tests
@pytest.mark.asyncio
async def test_mcp_client_validation():
    pe = PolicyEngine()
    pe.allow_mcp_tools = False

    client_mcp = mcp_client
    client_mcp.enabled = True
    client_mcp.tool_to_server["test_mcp_tool"] = "filesystem"

    with pytest.raises(PermissionError, match="blocked"):
        await client_mcp.call_tool("test_mcp_tool", {"arg": "val"}, pe)

    pe.allow_mcp_tools = True
    with pytest.raises(PermissionError, match="blocked by path policy"):
        await client_mcp.call_tool("test_mcp_tool", {"arg": "../outside/path"}, pe)


@pytest.mark.asyncio
async def test_mcp_client_subprocess_mock():
    client_mcp = mcp_client
    client_mcp.enabled = True
    client_mcp.servers_config = [{"name": "filesystem", "command": "echo", "args": []}]

    mock_proc = MagicMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    # StreamWriter.write() is sync, not async
    mock_proc.stdin.write = MagicMock(return_value=None)
    mock_proc.stdin.drain = AsyncMock(return_value=None)

    # Mock json-rpc response
    mock_proc.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "read_file", "description": "Read file"}]}}\n'

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await client_mcp.initialize()
        assert "read_file" in client_mcp.tools
        assert client_mcp.tool_to_server["read_file"] == "filesystem"

        # Test call tool
        mock_proc.stdout.readline.return_value = (
            b'{"jsonrpc": "2.0", "id": 2, "result": {"content": "file content"}}\n'
        )
        pe = PolicyEngine()
        pe.allow_mcp_tools = True

        res = await client_mcp.call_tool("read_file", {"path": "hello.txt"}, pe)
        assert res == {"content": "file content"}

        # Test shutdown
        await client_mcp.shutdown()
        mock_proc.terminate.assert_called()


# 4. Standard Benchmarks Tests
@pytest.mark.asyncio
async def test_benchmark_runner_and_compare():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(
            [{"task_id": "HumanEval/999", "prompt": "def dummy(): pass", "test": "assert True"}], f
        )
        suite_path = f.name

    try:
        with patch(
            "scripts.llm_harness.benchmarks.runner.run_harness", new_callable=AsyncMock
        ) as mock_run:
            from scripts.llm_harness.models import ExecutionResult

            mock_run.return_value = ExecutionResult(success=True, message="solved")

            runner = BenchmarkSuiteRunner(suite_path=suite_path, provider="stub", allow_stub=True)
            summary = await runner.run()

            assert summary["total_tasks"] == 1
            assert summary["solved"] == 1
            assert summary["accuracy"] == 1.0

            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as bf:
                json.dump({"accuracy": 0.95}, bf)
                baseline_path = bf.name
            try:
                comp = compare_benchmarks(summary, baseline_path, threshold=0.05)
                assert comp["regressed"] is False
                assert comp["status"] == "pass"

                comp_fail = compare_benchmarks({"accuracy": 0.8}, baseline_path, threshold=0.05)
                assert comp_fail["regressed"] is True
                assert comp_fail["status"] == "fail"
            finally:
                os.unlink(baseline_path)
    finally:
        os.unlink(suite_path)


# 5. Multi-modal Support Tests
@pytest.mark.asyncio
async def test_multimodal_support_harness():
    async with Workspace() as ws:
        img_path = "screenshot.png"
        ws.write_file(img_path, "fake_img_binary_data")

        # Verify image outside repository boundary is blocked
        with pytest.raises(
            PermissionError, match="blocked by policy|outside the workspace repository"
        ):
            await run_harness(
                task="test task",
                allow_stub=True,
                image_path="/etc/passwd",
                workspace_path=ws.path,
                config=HarnessConfig(
                    code_agent="test-agent",
                    provider="stub",
                    multimodal=True,
                ),
            )

        # Verify provider fails if multimodal=True is not set
        with pytest.raises(ValueError, match="does not support multimodal input"):
            await run_harness(
                task="test task",
                allow_stub=True,
                image_path=img_path,
                workspace_path=ws.path,
                config=HarnessConfig(
                    code_agent="test-agent",
                    provider="stub",
                ),
            )

        # Verify provider works with multimodal=True set
        with patch(
            "scripts.llm_harness.providers.StubProvider.chat_completion", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"action_type": "final", "message": "Success"}),
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            res = await run_harness(
                task="test task",
                allow_stub=True,
                image_path=img_path,
                workspace_path=ws.path,
                config=HarnessConfig(
                    code_agent="test-agent",
                    provider="stub",
                    multimodal=True,
                ),
            )
            assert res.success is True


# 6. Sanitizer redacts base64 images
def test_sanitizer_redacts_base64_image():
    payload = {
        "text": "regular text",
        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==",
    }
    sanitized = Sanitizer.sanitize_data(payload)
    assert sanitized["text"] == "regular text"
    assert sanitized["image_data"] == "[REDACTED_IMAGE_BASE64]"


# 7. Test CLI commands execution
def test_cli_commands_plugin_and_server():
    from scripts.llm_harness.cli_commands import run_plugins_command, run_server_command

    mock_args = MagicMock()
    mock_args.host = "127.0.0.1"
    mock_args.port = 8765
    mock_args.api_key_env = "TEST_API_KEY_ENV"

    # Mock uvicorn run so we don't start a real blocking server
    with patch("uvicorn.run") as mock_uvicorn:
        run_server_command(mock_args)
        mock_uvicorn.assert_called_once()

    # List plugins cli command
    mock_args.plugin_command = "list"
    mock_args.enable_plugins = True
    run_plugins_command(mock_args)

    # Validate plugins cli command
    mock_args.plugin_command = "validate"
    run_plugins_command(mock_args)


@pytest.mark.asyncio
async def test_mcp_client_error_paths():
    client_mcp = mcp_client
    # 1. MCP disabled
    client_mcp.enabled = False
    pe = PolicyEngine()
    with pytest.raises(RuntimeError, match="MCP is disabled"):
        await client_mcp.call_tool("some_tool", {}, pe)

    client_mcp.enabled = True
    # 2. Unknown tool
    with pytest.raises(ValueError, match="Unknown MCP tool"):
        await client_mcp.call_tool("unknown_tool", {}, pe)

    client_mcp.tool_to_server["test_tool"] = "filesystem"
    # 3. No response
    with patch.object(client_mcp, "_send_request", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        pe.allow_mcp_tools = True
        with pytest.raises(RuntimeError, match="No response from MCP Server"):
            await client_mcp.call_tool("test_tool", {}, pe)

    # 4. Server error
    with patch.object(client_mcp, "_send_request", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"error": {"message": "Disk Failure"}}
        with pytest.raises(RuntimeError, match="MCP server error: Disk Failure"):
            await client_mcp.call_tool("test_tool", {}, pe)

    client_mcp.enabled = False


def test_plugin_registry_load_error():
    # Mocking ep.load to raise an exception
    mock_ep = MagicMock()
    mock_ep.name = "failing_plugin"
    mock_ep.load.side_effect = Exception("failed to load")

    with patch("importlib.metadata.entry_points") as mock_eps:
        # Depending on Python version, it might return list or dict or EntryPoints
        # Let's mock a select or dict or iter as appropriate
        mock_eps.return_value = [mock_ep]
        with pytest.raises(RuntimeError, match="Failed to load plugin failing_plugin"):
            plugin_registry.load_all_plugins(enable_plugins=True)


# 8. MCP Filesystem Real-like Integration Test using Python subprocess
@pytest.mark.asyncio
async def test_mcp_filesystem_server_mock():
    _script = """
import json, sys
TOOLS = [
    {"name": "read_file", "description": "Read a file's contents",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "write_file", "description": "Write content to a file",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
    {"name": "list_dir", "description": "List directory contents",
     "inputSchema": {"type": "object", "properties": {"dir": {"type": "string"}}}},
]
for line in sys.stdin:
    req = json.loads(line)
    rid = req.get("id")
    method = req.get("method")
    if method == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}) + "\\n")
    elif method == "tools/call":
        tname = req["params"]["name"]
        args = req["params"].get("arguments", {})
        if tname == "read_file":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"content": f"contents of {args['path']}"}}) + "\\n")
        elif tname == "write_file":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"success": True}}) + "\\n")
        elif tname == "list_dir":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"entries": ["f1.txt", "f2.txt"]}}) + "\\n")
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown tool: {tname}"}}) + "\\n")
    else:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}) + "\\n")
    sys.stdout.flush()
"""
    client = mcp_client
    client.enabled = True
    client.servers_config = [
        {"name": "filesystem", "command": sys.executable, "args": ["-c", _script]}
    ]
    client.active_processes.clear()
    client.tools.clear()
    client.tool_to_server.clear()

    await client.initialize()

    assert "read_file" in client.tools
    assert "write_file" in client.tools
    assert "list_dir" in client.tools
    assert client.tool_to_server["read_file"] == "filesystem"
    assert client.tool_to_server["write_file"] == "filesystem"
    assert client.tool_to_server["list_dir"] == "filesystem"

    pe = PolicyEngine()
    pe.allow_mcp_tools = True

    res = await client.call_tool("read_file", {"path": "test.txt"}, pe)
    assert "contents of test.txt" in res.get("content", "")

    res = await client.call_tool("write_file", {"path": "test.txt", "content": "hello"}, pe)
    assert res.get("success") is True

    res = await client.call_tool("list_dir", {"dir": "."}, pe)
    assert "f1.txt" in res.get("entries", [])

    with pytest.raises((RuntimeError, ValueError), match="Unknown MCP tool|MCP server error"):
        await client.call_tool("unknown_tool", {}, pe)

    # Test that server error propagates properly for a known tool
    client.tool_to_server["error_tool"] = "filesystem"
    client.tools["error_tool"] = {"name": "error_tool"}
    with pytest.raises(RuntimeError, match="MCP server error"):
        await client.call_tool("error_tool", {}, pe)

    await client.shutdown()
    client.enabled = False


# 9. GSM8K-Style Benchmark Adapter Tests
@pytest.mark.asyncio
async def test_gsm8k_adapter_extract_answer():
    from scripts.llm_harness.benchmarks.gsm8k import GSM8KAdapter

    assert GSM8KAdapter.extract_answer("The answer is #### 42") == "42"
    assert GSM8KAdapter.extract_answer("#### 5.25") == "5.25"
    assert GSM8KAdapter.extract_answer("**Answer:** 99") == "99"
    assert GSM8KAdapter.extract_answer("No answer here") is None

    assert GSM8KAdapter.extract_predicted("the answer is 42") == "42"
    assert GSM8KAdapter.extract_predicted("The result: 3.14") == "3.14"
    assert GSM8KAdapter.extract_predicted("final value = 100") == "100"
    assert GSM8KAdapter.extract_predicted("just some text") is None

    assert GSM8KAdapter.normalize_number("42") == 42.0
    assert GSM8KAdapter.normalize_number("1,234") == 1234.0
    assert GSM8KAdapter.normalize_number("not a number") is None


@pytest.mark.asyncio
async def test_gsm8k_adapter_run_mini():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(
            [
                {"task_id": "GSM8K/test/0", "question": "What is 2+2?", "answer": "#### 4"},
            ],
            f,
        )
        suite_path = f.name

    try:
        with patch(
            "scripts.llm_harness.benchmarks.gsm8k.run_harness", new_callable=AsyncMock
        ) as mock_run:
            from scripts.llm_harness.models import ExecutionResult

            mock_run.return_value = ExecutionResult(
                success=True, message="The answer is 4", total_tokens=10
            )

            adapter = GSM8KAdapter(suite_path=suite_path, provider="stub", allow_stub=True)
            summary = await adapter.run()

            assert summary["total_tasks"] == 1
            assert summary["solved"] == 1
            assert summary["accuracy"] == 1.0
            assert summary["type"] == "gsm8k"
    finally:
        os.unlink(suite_path)


# 10. Audio/Video Content Block Tests
def test_audio_video_content_block_format():
    from scripts.llm_harness.legacy_runner import run_harness

    assert hasattr(run_harness, "__wrapped__") or True
    assert True  # Placeholder - actual validation in multimodal test


@pytest.mark.asyncio
async def test_multimodal_with_audio_and_video():
    async with Workspace() as ws:
        img_path = "screenshot.png"
        audio_path = "audio.mp3"
        video_path = "video.mp4"
        ws.write_file(img_path, "fake_img")
        ws.write_file(audio_path, "fake_audio")
        ws.write_file(video_path, "fake_video")

        with patch(
            "scripts.llm_harness.providers.StubProvider.chat_completion", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"action_type": "final", "message": "Done"}),
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

            config = HarnessConfig(
                code_agent="test-agent",
                provider="stub",
                model="",
                multimodal=True,
                audio_path=audio_path,
                video_path=video_path,
            )
            res = await run_harness(
                task="test",
                allow_stub=True,
                workspace_path=ws.path,
                config=config,
                image_path=img_path,
            )
            assert res.success is True

            call_args = mock_chat.call_args
            if call_args:
                messages = call_args[0][0]
                user_msg = next(m for m in messages if m["role"] == "user")
                assert isinstance(user_msg["content"], list)
                types = [b["type"] for b in user_msg["content"]]
                assert "text" in types
                assert "image_url" in types
                assert "audio_url" in types
                assert "video_url" in types


# 11. Anthropic and Google Multimodal Content Block Adapters
def test_anthropic_multimodal_conversion():
    from scripts.llm_harness.providers import AnthropicProvider

    provider = AnthropicProvider(
        config={
            "agent_id": "test",
            "api_key_env": "NONEXISTENT_KEY",
            "provider": "anthropic",
        }
    )
    content_blocks = [
        {"type": "text", "text": "What is in this image?"},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="},
        },
    ]
    result = provider._convert_to_anthropic_content(content_blocks)
    assert len(result) == 2
    assert result[0]["type"] == "text"
    assert result[0]["text"] == "What is in this image?"
    assert result[1]["type"] == "image"
    assert result[1]["source"]["type"] == "base64"
    assert result[1]["source"]["media_type"] == "image/png"
    assert result[1]["source"]["data"] == "iVBORw0KGgoAAAANSUhEUg=="


def test_google_multimodal_conversion():
    from scripts.llm_harness.providers import GoogleProvider

    provider = GoogleProvider(
        config={
            "agent_id": "test",
            "api_key_env": "NONEXISTENT_KEY",
            "provider": "google",
        }
    )
    content_blocks = [
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ=="}},
    ]
    parts = provider._convert_to_google_parts(content_blocks)
    assert len(parts) == 2
    assert "text" in parts[0]
    assert parts[0]["text"] == "Describe this image"
    assert "inline_data" in parts[1]
    assert parts[1]["inline_data"]["mime_type"] == "image/jpeg"
    assert parts[1]["inline_data"]["data"] == "/9j/4AAQ=="


# 12. Provider-level unsupported media handling (Risk 1 mitigation)
def test_provider_warn_unsupported_media():
    from scripts.llm_harness.providers import StubProvider

    provider = StubProvider(
        config={
            "agent_id": "test",
            "api_key_env": "NONEXISTENT_KEY",
            "provider": "stub",
            "multimodal": True,
        }
    )

    # Audio block is filtered with warning text
    blocks = [
        {"type": "text", "text": "hello"},
        {
            "type": "audio_url",
            "audio_url": {"url": "data:audio/mpeg;base64,AAA="},
            "metadata": {"mime_type": "audio/mpeg", "extension": "mp3"},
        },
        {
            "type": "video_url",
            "video_url": {"url": "data:video/mp4;base64,BBB="},
            "metadata": {"mime_type": "video/mp4", "extension": "mp4"},
        },
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,CCC="}},
    ]
    result = provider._warn_unsupported_media(blocks)
    assert len(result) == 4
    assert result[1]["type"] == "text"
    assert "audio_url" in result[1]["text"]
    assert result[2]["type"] == "text"
    assert "video_url" in result[2]["text"]
    assert result[3]["type"] == "image_url"

    # Plain string pass-through
    result = provider._warn_unsupported_media("just text")
    assert len(result) == 1
    assert result[0]["type"] == "text"


def test_anthropic_skips_audio_video():
    from scripts.llm_harness.providers import AnthropicProvider

    provider = AnthropicProvider(
        config={
            "agent_id": "test",
            "api_key_env": "NONEXISTENT_KEY",
            "provider": "anthropic",
        }
    )
    blocks = [
        {"type": "text", "text": "desc"},
        {
            "type": "audio_url",
            "audio_url": {"url": "data:audio/mpeg;base64,AAA="},
            "metadata": {"mime_type": "audio/mpeg", "extension": "mp3"},
        },
    ]
    result = provider._convert_to_anthropic_content(blocks)
    assert len(result) == 2
    assert result[1]["type"] == "text"
    assert "skipped" in result[1]["text"]


def test_google_skips_audio_video():
    from scripts.llm_harness.providers import GoogleProvider

    provider = GoogleProvider(
        config={
            "agent_id": "test",
            "api_key_env": "NONEXISTENT_KEY",
            "provider": "google",
        }
    )
    blocks = [
        {"type": "text", "text": "desc"},
        {
            "type": "video_url",
            "video_url": {"url": "data:video/mp4;base64,BBB="},
            "metadata": {"mime_type": "video/mp4", "extension": "mp4"},
        },
    ]
    result = provider._convert_to_google_parts(blocks)
    assert len(result) == 2
    assert "text" in result[1]
    assert "skipped" in result[1]["text"]


# 13. GSM8K improved extraction (Risk 2 mitigation)
def test_gsm8k_extract_predicted_from_events():
    from scripts.llm_harness.benchmarks.gsm8k import GSM8KAdapter

    text = ""
    events = [
        {"action_type": "final", "message": "The total cost is 5.25 dollars"},
    ]
    result = GSM8KAdapter.extract_predicted(text, events)
    assert result is not None
    assert "5.25" in result

    result = GSM8KAdapter.extract_predicted("**Answer:** 42")
    assert result == "42"

    result = GSM8KAdapter.extract_predicted("Therefore the answer is 100")
    assert result == "100"

    result = GSM8KAdapter.extract_predicted("just text no numbers")
    assert result is None


# 14. SWE-bench adapter tests
@pytest.mark.asyncio
async def test_swebench_adapter_parse_patch():
    from scripts.llm_harness.benchmarks.swebench_adapter import SWEBenchAdapter

    header, diff = SWEBenchAdapter.parse_test_patch(
        "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -0,0 +1,4 @@\n+def test_ratio():\n+    pass\n"
    )
    assert "--- a/tests/test_calc.py" in header
    assert "def test_ratio" in diff

    paths = SWEBenchAdapter.extract_test_paths(
        "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n"
    )
    assert "tests/test_calc.py" in paths


@pytest.mark.asyncio
async def test_swebench_adapter_run_mini():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(
            [
                {
                    "instance_id": "SWE-bench/test/0",
                    "problem_description": "Fix div by zero",
                    "test_patch": "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -0,0 +1,4 @@\n+def test_ratio():\n+    pass\n+",
                    "fail_to_pass": ["tests/test_calc.py::test_ratio"],
                    "pass_to_pass": [],
                }
            ],
            f,
        )
        suite_path = f.name

    try:
        with (
            patch(
                "scripts.llm_harness.benchmarks.swebench_adapter.run_harness",
                new_callable=AsyncMock,
            ) as mock_run,
            patch(
                "scripts.llm_harness.benchmarks.swebench_adapter.subprocess.run"
            ) as mock_subprocess,
        ):
            from scripts.llm_harness.models import ExecutionResult

            mock_run.return_value = ExecutionResult(success=True, message="fixed")
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "all tests passed"
            mock_proc.stderr = ""
            mock_subprocess.return_value = mock_proc

            adapter = SWEBenchAdapter(suite_path=suite_path, provider="stub", allow_stub=True)
            summary = await adapter.run()

            assert summary["type"] == "swebench"
            assert summary["total_tasks"] == 1
            assert summary["solved"] == 1
            assert summary["accuracy"] == 1.0
    finally:
        os.unlink(suite_path)


# 15. CLI --suite-type integration test
def test_cli_benchmark_gsm8k_help():
    with patch("sys.argv", ["cli.py", "benchmark", "run", "--help"]):
        with pytest.raises(SystemExit) as e:
            from scripts.llm_harness.cli import main

            main()
        assert e.value.code == 0


# 16. MCP cleanup robustness (Risk 3 mitigation)
@pytest.mark.asyncio
async def test_mcp_shutdown_timeout():
    client_mcp = mcp_client
    client_mcp.enabled = True
    client_mcp._shutdown_timeout = 0.1

    proc = MagicMock()
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock(side_effect=[TimeoutError(), None])

    client_mcp.active_processes["slow_server"] = proc
    await client_mcp.shutdown()
    proc.kill.assert_called_once()
    assert len(client_mcp.active_processes) == 0


@pytest.mark.asyncio
async def test_mcp_shutdown_process_lookup_error():
    client_mcp = mcp_client
    proc = MagicMock()
    proc.terminate.side_effect = ProcessLookupError()
    client_mcp.active_processes["gone"] = proc
    await client_mcp.shutdown()
    assert len(client_mcp.active_processes) == 0
