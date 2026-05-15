import pytest
from app.services.governance.rego_runtime import RegoRuntime

def test_rego_runtime_load_bundle():
    runtime = RegoRuntime()
    hash_val = runtime.load_bundle("package test\n\ndefault allow = false\n")
    assert hash_val is not None
    assert len(hash_val) > 0

def test_rego_runtime_evaluate_allow():
    runtime = RegoRuntime(mode="enforce")
    result = runtime.evaluate("com.example.policy", {"action": "read"}, {"tenant_id": "1234"})
    
    assert "result" in result
    res = result["result"]
    assert res["allow"] is True
    assert res["deny"] is False
    assert len(res["violations"]) == 0
    assert "rule_default_allow" in res["matched_rules"]

def test_rego_runtime_evaluate_restrict():
    runtime = RegoRuntime(mode="enforce")
    result = runtime.evaluate("com.example.policy", {"action": "restrict_access"}, {"tenant_id": "1234"})
    
    assert "result" in result
    res = result["result"]
    assert res["allow"] is False
    assert res["deny"] is True
    assert len(res["violations"]) == 1
    assert res["violations"][0]["code"] == "com.example.policy.RESTRICTED_ACTION"
