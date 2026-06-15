import pytest
from app.core.config import get_settings
from app.services.agents.code_interpreter.providers.mock_sandbox import MockSandboxProvider
from app.services.agents.code_interpreter.sandbox_limits import ExecutionLimits
from app.services.agents.code_interpreter.sandbox_policy import (
    SandboxPolicyEngine,
    SandboxPolicyViolation,
)


@pytest.mark.asyncio
async def test_block_env_read():
    policy = SandboxPolicyEngine()
    code = "import os\nwith open('.env', 'r') as f: print(f.read())"
    # Even if open is blocked by FORBIDDEN_CALLS, the path check should catch it first or as well
    with pytest.raises(
        SandboxPolicyViolation,
        match="Access to protected path is not allowed|Import of 'os' is not allowed|Call to 'open' is not allowed",
    ):
        policy.validate_code(code)


@pytest.mark.asyncio
async def test_block_subprocess():
    policy = SandboxPolicyEngine()
    code = "import subprocess\nsubprocess.run(['ls'])"
    with pytest.raises(SandboxPolicyViolation, match="Import of 'subprocess' is not allowed"):
        policy.validate_code(code)


@pytest.mark.asyncio
async def test_block_network():
    policy = SandboxPolicyEngine()
    code = "url = 'https://google.com'\nprint(url)"
    with pytest.raises(SandboxPolicyViolation, match="Network access is disabled by default"):
        policy.validate_code(code)


@pytest.mark.asyncio
async def test_timeout_works():
    provider = MockSandboxProvider()
    limits = ExecutionLimits(timeout_seconds=1)
    # Mock provider simulates timeout for "while True"
    code = "while True: pass"
    result = await provider.run(code, limits)
    assert result["exit_code"] == 124
    assert "timed out" in result["stderr"]


@pytest.mark.asyncio
async def test_output_truncation():
    policy = SandboxPolicyEngine()
    output = "A" * 1000
    max_bytes = 100
    truncated_output, is_truncated = policy.truncate_output(output, max_bytes)
    assert is_truncated
    assert len(truncated_output.encode("utf-8")) <= max_bytes + len("\n...[truncated]")
    assert "...[truncated]" in truncated_output


@pytest.mark.asyncio
async def test_artifact_secret_blocking():
    policy = SandboxPolicyEngine()
    # AWS Access Key ID pattern
    secret_content = b"My secret key is AKIA123456789012"
    with pytest.raises(SandboxPolicyViolation, match="Artifact contains secret-like content"):
        policy.validate_artifact_content(secret_content)


@pytest.mark.asyncio
async def test_provider_unavailable_no_simulated_success():
    settings = get_settings()
    settings.agent_sandbox_allow_simulated_provider = False

    policy = SandboxPolicyEngine()
    # If a provider is 'mock' but simulated is NOT allowed, it should fail
    with pytest.raises(SandboxPolicyViolation, match="Simulated provider 'mock' is not allowed"):
        policy.validate_provider("mock", is_simulated=True)


@pytest.mark.asyncio
async def test_forbidden_calls_getattr():
    policy = SandboxPolicyEngine()
    code = "getattr(object, 'attr')"
    with pytest.raises(SandboxPolicyViolation, match="Call to 'getattr' is not allowed"):
        policy.validate_code(code)


@pytest.mark.asyncio
async def test_forbidden_calls_exec():
    policy = SandboxPolicyEngine()
    code = "exec('print(1)')"
    with pytest.raises(SandboxPolicyViolation, match="Call to 'exec' is not allowed"):
        policy.validate_code(code)
