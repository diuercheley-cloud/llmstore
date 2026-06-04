import os
from unittest.mock import AsyncMock, patch

import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.cli import _resolve_code_agent, main
from scripts.llm_harness.cli_commands import _validate_provider_settings
from scripts.llm_harness.config import HarnessConfig


def test_cli_help():
    with patch("sys.argv", ["cli.py", "--help"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0

def test_cli_health_local():
    with patch("sys.argv", ["cli.py", "health", "--local-only"]):
        main()

def test_cli_code_no_config_fail():
    with patch("sys.argv", ["cli.py", "code", "--task", "fix"]):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1

def test_cli_code_allow_stub():
    with patch("sys.argv", ["cli.py", "code", "--task", "fix", "--allow-stub-code-agent"]):
        with patch.dict(os.environ, {}, clear=True):
            # Should not exit 1
            main()


def test_cli_code_prints_progress(capsys):
    with patch("sys.argv", ["cli.py", "code", "--task", "fix", "--allow-stub-code-agent"]):
        with patch.dict(os.environ, {}, clear=True):
            main()
    captured = capsys.readouterr()
    assert "run.started" in captured.out
    assert "run.completed" in captured.out

def test_cli_code_with_config_auto_select():
    with patch(
        "sys.argv",
        [
            "cli.py",
            "code",
            "--task",
            "fix",
            "--base-url",
            "http://localhost:18080",
            "--model",
            "test-model",
        ],
    ):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch.object(
                AgentClient,
                "chat_completion",
                AsyncMock(
                    return_value={
                        "choices": [
                            {"message": {"role": "assistant", "content": '{"final":"done"}'}}
                        ]
                    }
                ),
            ):
                main()

def test_cli_code_explicit_provider():
    with patch(
        "sys.argv",
        [
            "cli.py",
            "code",
            "--task",
            "fix",
            "--provider",
            "openai-compatible",
            "--base-url",
            "http://localhost:18080",
            "--model",
            "test-model",
        ],
    ):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch.object(
                AgentClient,
                "chat_completion",
                AsyncMock(
                    return_value={
                        "choices": [
                            {"message": {"role": "assistant", "content": '{"final":"done"}'}}
                        ]
                    }
                ),
            ):
                main()


def test_cli_security_check_only(capsys):
    with patch("sys.argv", ["cli.py", "security", "--check-only"]):
        main()
    captured = capsys.readouterr()
    assert "Security Audit:" in captured.out
    assert "sanitizer_redacts_secrets: OK" in captured.out


class FakeArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_resolve_code_agent_defaults_to_openai_compatible():
    """Without --allow-stub-code-agent, must default to openai-compatible."""
    args = FakeArgs(code_agent=None, provider=None, allow_stub_code_agent=False)
    assert _resolve_code_agent(args) == "openai-compatible"


def test_resolve_code_agent_allow_stub_returns_stub():
    """With --allow-stub-code-agent, must return stub."""
    args = FakeArgs(code_agent=None, provider=None, allow_stub_code_agent=True)
    assert _resolve_code_agent(args) == "stub"


def test_resolve_code_agent_explicit_provider_wins():
    """Explicit --provider must override defaults."""
    args = FakeArgs(
        code_agent="anthropic",
        provider="anthropic",
        allow_stub_code_agent=False,
    )
    assert _resolve_code_agent(args) == "anthropic"


def test_resolve_code_agent_explicit_code_agent_wins():
    """Explicit --code-agent must win over allow_stub."""
    args = FakeArgs(
        code_agent="google",
        provider=None,
        allow_stub_code_agent=True,
    )
    assert _resolve_code_agent(args) == "google"


def test_cli_code_no_config_fail_message():
    """Must mention missing config, not silently use stub."""
    with patch("sys.argv", ["cli.py", "code", "--task", "fix"]):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1


def test_extracted_config_builders():
    from scripts.llm_harness.cli_commands import (
        build_config_overrides,
        build_provider_config,
        build_sandbox_config,
    )

    args = FakeArgs(
        config="custom_config.toml",
        agent_id="test-agent",
        model="gpt-5",
        base_url="https://api.openai.com/v1",
        sandbox=True,
        docker_image="python:3.13-slim",
        self_heal=False,
        api_key_env="CUSTOM_KEY",
        timeout=15.5,
        local_model_timeout=300.0,
        auto_increase_timeout=True,
        max_retries=5,
        stream=True,
        stream_local_default=True,
        verbose_stream=True,
        tool_calling="auto",
        supports_tool_calling=True,
        workspace_mount_path="/mnt",
        temp_base_dir="/tmp/harness",
        sandbox_network="host",
        proxy_url="http://proxy:8080",
        loop_timeout=60,
        max_output_chars=5000,
        report_output_path="out/",
        cache="llm",
        no_cache=False,
        cache_dir=".cache",
        pricing_file="pricing.json",
        max_cost_per_run=10.0,
        max_tokens_per_run=10000,
        memory="local",
        memory_dir=".mem",
        memory_retention_days=15,
        agent_mode="single",
        approval_mode="auto",
        approval_default="deny",
        edit_action_before_run=True,
        checkpoint_dir=".checkpoints",
        checkpoint_every_step=True,
        code_agent="openai-compatible",
        allow_stub_code_agent=False,
    )

    overrides = build_config_overrides(args)
    assert overrides["config"] == "custom_config.toml"
    assert overrides["code_agent"] == "test-agent"
    assert overrides["model"] == "gpt-5"
    assert overrides["sandbox"] is True
    assert overrides["cache"] == "llm"
    assert overrides["local_model_timeout"] == 300.0
    assert overrides["tool_calling"] == "auto"
    assert overrides["supports_tool_calling"] is True

    provider_cfg = build_provider_config(args)
    assert provider_cfg["provider"] == "openai-compatible"
    assert provider_cfg["model"] == "gpt-5"
    assert provider_cfg["base_url"] == "https://api.openai.com/v1"
    assert provider_cfg["timeout"] == 15.5
    assert provider_cfg["stream_local_default"] is True
    assert provider_cfg["supports_tool_calling"] is True

    sandbox_cfg = build_sandbox_config(args)
    assert sandbox_cfg["sandbox"] is True
    assert sandbox_cfg["docker_image"] == "python:3.13-slim"
    assert sandbox_cfg["workspace_mount_path"] == "/mnt"
    assert sandbox_cfg["sandbox_network"] == "host"


def test_validate_local_openai_compatible_does_not_require_api_key():
    config = HarnessConfig(
        provider="local-openai-compatible",
        base_url="http://192.168.3.120:1234",
        model="qwen/qwen3.6-35b-a3b",
        api_key_env="OPENAI_API_KEY",
    )

    with patch.dict(os.environ, {}, clear=True):
        _validate_provider_settings("local-openai-compatible", config, allow_stub=False)


def test_validate_local_openai_compatible_allows_missing_model():
    config = HarnessConfig(
        provider="local-openai-compatible",
        base_url="http://192.168.3.120:1234",
        model="",
        api_key_env="OPENAI_API_KEY",
    )

    with patch.dict(os.environ, {}, clear=True):
        _validate_provider_settings("local-openai-compatible", config, allow_stub=False)


def test_validate_openai_compatible_still_requires_api_key():
    config = HarnessConfig(
        provider="openai-compatible",
        base_url="http://192.168.3.120:1234",
        model="qwen/qwen3.6-35b-a3b",
        api_key_env="OPENAI_API_KEY",
    )

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _validate_provider_settings("openai-compatible", config, allow_stub=False)
