import runpy
import subprocess
import sys
from unittest.mock import patch

import pytest


def test_cli_does_not_import_legacy():
    # If we import scripts.llm_harness.cli, it should not trigger import of scripts.agent_harness
    if "scripts.agent_harness" in sys.modules:
        del sys.modules["scripts.agent_harness"]
    if "scripts.llm_harness.cli" in sys.modules:
        del sys.modules["scripts.llm_harness.cli"]

    import scripts.llm_harness.cli  # noqa: F401

    assert "scripts.agent_harness" not in sys.modules


def test_legacy_wrapper_delegates_to_main():
    with patch("scripts.llm_harness.legacy_runner.main") as mock_main:
        runpy.run_path("scripts/agent_harness.py", run_name="__main__")
        mock_main.assert_called_once()


def test_legacy_wrapper_help():
    # Test that running python3 scripts/agent_harness.py --help outputs help message
    result = subprocess.run(
        [sys.executable, "scripts/agent_harness.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "LLM Harness Orchestrator" in result.stdout or "help" in result.stdout


def test_agent_test_sh_help():
    # Test that running ./scripts/agent-test.sh --help outputs usage
    result = subprocess.run(
        ["./scripts/agent-test.sh", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Usage: ./scripts/agent-test.sh" in result.stdout


def test_cli_help_option():
    # Test that python3 -m scripts.llm_harness.cli --help outputs help message
    result = subprocess.run(
        [sys.executable, "-m", "scripts.llm_harness.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "LLM Harness CLI" in result.stdout


@pytest.mark.asyncio
async def test_run_harness_legacy_compatibility():

    import pytest

    from scripts.llm_harness.legacy_runner import run_harness

    # Should raise deprecation warning when called without config
    with pytest.deprecated_call():
        res = await run_harness(
            agent_id="test-agent",
            task="do nothing",
            timeout=10,
            provider="stub",
            allow_stub=True,
            memory_mode="disabled",
            cache_mode="disabled",
        )
    assert res is not None


@pytest.mark.asyncio
async def test_run_harness_with_config():
    import warnings

    from scripts.llm_harness.config import HarnessConfig
    from scripts.llm_harness.legacy_runner import run_harness

    config = HarnessConfig(
        code_agent="stub",
        memory="disabled",
        cache="disabled",
    )
    # Passing config directly shouldn't emit a DeprecationWarning
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        res = await run_harness(
            task="do nothing",
            config=config,
            allow_stub=True,
        )
    assert res is not None

