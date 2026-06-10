import pytest
from app.services.agents.code_interpreter.providers.mock_sandbox import MockSandboxProvider
from app.services.agents.code_interpreter.sandbox_limits import ExecutionLimits
from app.services.agents.code_interpreter.sandbox_policy import (
    SandboxPolicyEngine,
    SandboxPolicyViolation,
)


def test_attempt_to_read_dotenv_is_blocked():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="protected path"):
        policy.validate_code("print('.env')")


def test_attempt_to_read_etc_passwd_is_blocked():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="protected path"):
        policy.validate_code("path='/etc/passwd'\nprint(path)")


def test_attempt_to_spawn_subprocess_is_blocked():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="subprocess"):
        policy.validate_code("import subprocess\nsubprocess.run(['id'])")


def test_attempt_to_use_network_is_blocked_by_default():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="Network access"):
        policy.validate_code("print('https://example.com')")


@pytest.mark.asyncio
async def test_timeout_path_returns_124():
    provider = MockSandboxProvider()
    result = await provider.run("while True:\n    pass", ExecutionLimits(timeout_seconds=1))
    assert result["exit_code"] == 124


def test_output_flooding_is_truncated():
    policy = SandboxPolicyEngine()
    text, truncated = policy.truncate_output("A" * 1024, 32)
    assert truncated is True
    assert "[truncated]" in text
