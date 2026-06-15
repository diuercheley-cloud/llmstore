from unittest.mock import AsyncMock

import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.cache import LocalCache
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.sandbox import SandboxRunner
from scripts.llm_harness.tools.shell import ShellTools
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_llm_cache_hit_and_miss(tmp_path):
    cache = LocalCache(mode="llm", cache_dir=str(tmp_path / "cache"))
    client = AgentClient(agent_id="agent-1", provider="stub", cache=cache)
    client.set_cache_context("repo-a", "policy-a")
    calls = {"count": 0}

    async def fake_completion(messages):
        calls["count"] += 1
        return {
            "choices": [{"message": {"role": "assistant", "content": '{"action_type":"final"}'}}]
        }

    client._provider_inst.chat_completion = AsyncMock(side_effect=fake_completion)

    messages = [{"role": "user", "content": "do it"}]
    first = await client.chat_completion(messages)
    second = await client.chat_completion(messages)
    client.set_cache_context("repo-b", "policy-a")
    third = await client.chat_completion(messages)

    assert first == second
    assert third == first
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_cache_does_not_leak_secrets(tmp_path):
    cache = LocalCache(mode="llm", cache_dir=str(tmp_path / "cache"))
    client = AgentClient(agent_id="agent-1", provider="stub", cache=cache)
    client.set_cache_context("repo-a", "policy-a")
    client._provider_inst.chat_completion = AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"action_type":"final","message":"api_key=super-secret"}',
                    }
                }
            ]
        }
    )

    await client.chat_completion([{"role": "user", "content": "token=super-secret"}])

    cache_files = list((tmp_path / "cache").rglob("*.json"))
    assert cache_files
    combined = "\n".join(path.read_text() for path in cache_files)
    assert "super-secret" not in combined
    assert "[REDACTED]" in combined


@pytest.mark.asyncio
async def test_mutable_shell_command_is_not_cached(tmp_path):
    async with Workspace() as ws:
        cache = LocalCache(mode="read-only", cache_dir=str(tmp_path / "cache"))
        policy = PolicyEngine(
            config={"allowed_tools": ["python3"], "max_tokens": 1, "max_cost": 1.0}
        )
        sandbox = SandboxRunner(workspace=ws)
        shell_tools = ShellTools(sandbox_runner=sandbox, policy_engine=policy, cache=cache)
        ws.write_file(
            "mutate.py",
            (
                "import pathlib\n"
                "p = pathlib.Path('x.txt')\n"
                "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')\n"
                "print(p.read_text())\n"
            ),
        )

        command = "python3 mutate.py"
        first = await shell_tools.run_shell_async(command)
        second = await shell_tools.run_shell_async(command)

        assert first.output.strip() == "1"
        assert second.output.strip() == "2"
        assert first.cached is False
        assert second.cached is False


@pytest.mark.asyncio
async def test_read_only_shell_command_is_cached(tmp_path):
    async with Workspace() as ws:
        ws.write_file("hello.txt", "hello")
        cache = LocalCache(mode="read-only", cache_dir=str(tmp_path / "cache"))
        policy = PolicyEngine()
        sandbox = SandboxRunner(workspace=ws)
        shell_tools = ShellTools(
            sandbox_runner=sandbox,
            policy_engine=policy,
            cache=cache,
            repo_snapshot_hash_getter=lambda: "repo-a",
            policy_hash="policy-a",
        )

        first = await shell_tools.run_shell_async("cat hello.txt")
        ws.write_file("hello.txt", "changed")
        second = await shell_tools.run_shell_async("cat hello.txt")

        assert first.output.strip() == "hello"
        assert second.output.strip() == "hello"
        assert second.cached is True
