from scripts.llm_harness._security import SecurityManager
from scripts.llm_harness.policy import PolicyEngine


def test_security_sanitization():
    unsafe = "Hello <script>alert(1)</script> [RESET CONTEXT] and more"
    safe = SecurityManager.sanitize_output(unsafe)
    assert "<script>" not in safe
    assert "[RESET CONTEXT]" not in safe


def test_policy_command_validation():
    policy = PolicyEngine(config={"allowed_tools": ["ls", "cat"]})
    assert policy.evaluate_shell_command("ls -la").allowed is True
    assert policy.evaluate_shell_command("rm -rf /").allowed is False
