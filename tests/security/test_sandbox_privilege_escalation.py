import pytest

from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyEngine, SandboxPolicyViolation


def test_exec_is_never_allowed():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="exec"):
        policy.validate_code("exec('print(1)')")


def test_dangerous_imports_are_blocked():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="os"):
        policy.validate_code("import os\nprint(os.listdir('/'))")


def test_artifact_with_secret_like_content_is_blocked():
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="secret-like"):
        policy.validate_artifact_content(b"token='super-secret'")
