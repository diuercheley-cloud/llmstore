import os

from app.services.platform.profile_resolver import ProfileResolver


def test_appliance_profile_resolution(monkeypatch):
    monkeypatch.delenv("AGENT_RUNTIME_ENABLED", raising=False)
    resolver = ProfileResolver()
    result = resolver.resolve("appliance")
    assert result["profile"] == "appliance"
    assert result["flags"]["AGENT_RUNTIME_ENABLED"] is False
    assert result["flags"]["DISTRIBUTED_RUNTIME_ENABLED"] is False

def test_agentic_pilot_profile_resolution():
    resolver = ProfileResolver()
    result = resolver.resolve("agentic-pilot")
    assert result["profile"] == "agentic-pilot"
    assert result["flags"]["AGENT_RUNTIME_ENABLED"] is True
    assert result["flags"]["AGENT_CODE_SANDBOX_PROVIDER"] == "docker"

def test_agentic_production_profile_resolution():
    resolver = ProfileResolver()
    result = resolver.resolve("agentic-production")
    assert result["profile"] == "agentic-production"
    assert result["flags"]["AGENT_CODE_SANDBOX_PROVIDER"] == "gvisor"
    assert result["flags"]["AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER"] is False

def test_enterprise_distributed_profile_resolution():
    resolver = ProfileResolver()
    result = resolver.resolve("enterprise-distributed")
    assert result["profile"] == "enterprise-distributed"
    assert result["flags"]["DISTRIBUTED_RUNTIME_ENABLED"] is True
    assert result["flags"]["MULTI_CLUSTER_ENABLED"] is True

def test_conflict_detection():
    resolver = ProfileResolver()
    # Manually simulate a conflict
    flags = {
        "AGENT_CODE_SANDBOX_MICROVM_REQUIRED": True,
        "AGENT_CODE_SANDBOX_PROVIDER": "docker"
    }
    conflicts = resolver.detect_conflicts(flags)
    assert "MICROVM_REQUIRED but provider is set to docker" in conflicts

def test_override_handling():
    os.environ["AGENT_RUNTIME_ENABLED"] = "true"
    resolver = ProfileResolver()
    result = resolver.resolve("appliance")
    # Even in appliance, if env override is true, it should be true
    assert result["flags"]["AGENT_RUNTIME_ENABLED"] is True
    assert "AGENT_RUNTIME_ENABLED" in result["overrides"]
    del os.environ["AGENT_RUNTIME_ENABLED"]
