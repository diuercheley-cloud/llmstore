from unittest.mock import patch

import pytest

from scripts.llm_harness.cli_commands import run_health_command
from scripts.llm_harness.health import HealthCheck


@pytest.mark.asyncio
async def test_health_local_env():
    result = await HealthCheck.check_local_env()
    assert "status" in result
    assert "checks" in result
    assert "python_version" in result["checks"]


@pytest.mark.asyncio
async def test_health_provider():
    class HealthyClient:
        async def health_check(self):
            return {"status": "healthy", "provider": "openai-compatible"}

    result = await HealthCheck.check_provider(client=HealthyClient())
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_control_plane_sanitizes_exception():
    class BrokenClient:
        async def health_check(self):
            raise RuntimeError(
                "Authorization: Bearer secret-token api_key=sk-secret "
                "https://user:pass@example.com?token=abc123"
            )

    result = await HealthCheck.check_provider(client=BrokenClient())
    assert result["status"] == "unhealthy"
    assert "secret-token" not in result["error"]
    assert "sk-secret" not in result["error"]
    assert "user:pass@" not in result["error"]
    assert "token=abc123" not in result["error"]
    assert "[REDACTED]" in result["error"]


@pytest.mark.asyncio
async def test_health_local_env_detects_project_venv(monkeypatch):
    monkeypatch.setattr("scripts.llm_harness.health.sys.prefix", "/usr")
    monkeypatch.setattr("scripts.llm_harness.health.sys.base_prefix", "/usr")
    monkeypatch.setattr("scripts.llm_harness.health.sys.executable", "/usr/bin/python3")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    def fake_exists(path: str) -> bool:
        return path.endswith(".venv/bin/python") or path.endswith(".venv/bin/pytest")

    with patch("scripts.llm_harness.health.os.path.exists", side_effect=fake_exists), patch(
        "scripts.llm_harness.health.shutil.which",
        side_effect=lambda name: f"/usr/bin/{name}",
    ):
        result = await HealthCheck.check_local_env()

    assert result["status"] == "healthy"
    assert result["checks"]["venv_active"] is True


@pytest.mark.asyncio
async def test_run_health_command_respects_provider(monkeypatch, capsys):
    captured = {}

    class FakeArgs:
        local_only = False
        config = None
        provider = "local-openai-compatible"
        code_agent = None
        base_url = "http://192.168.3.120:1234"
        model = "qwen/qwen3.6-35b-a3b"
        api_key_env = "OPENAI_API_KEY"
        timeout = 30.0
        max_retries = 3
        stream = False

    async def fake_check_provider(client):
        captured["provider"] = client.provider
        return {
            "status": "healthy",
            "provider": client.provider,
            "details": {
                "selected_model": "qwen/qwen3.6-35b-a3b",
                "supports_native_tool_calling": False,
            },
        }

    async def fake_check_local_env():
        return {"status": "healthy", "checks": {}}

    monkeypatch.setattr(
        "scripts.llm_harness.health.HealthCheck.check_local_env",
        fake_check_local_env,
    )
    monkeypatch.setattr(
        "scripts.llm_harness.cli_commands.HealthCheck.check_provider",
        fake_check_provider,
    )

    await run_health_command(FakeArgs())
    captured_out = capsys.readouterr().out

    assert captured["provider"] == "local-openai-compatible"
    assert "selected_model: qwen/qwen3.6-35b-a3b" in captured_out
    assert "supports_native_tool_calling: False" in captured_out
