from app.services.governance.policy_trace import PolicyTraceBuilder


def test_policy_trace_builder():
    builder = PolicyTraceBuilder(evaluation_id="eval-123", bundle_id="bundle-abc")
    
    builder.add_matched_rule("rule_1", {"context": "val"})
    builder.add_failed_rule("rule_2", "invalid payload")
    builder.add_remediation_hint("ERR_01", "Fix the payload")
    
    trace = builder.finalize_trace("deny")
    
    assert trace["evaluation_id"] == "eval-123"
    assert "rule_1" in trace["matched_rules"]
    assert "rule_2" in trace["failed_rules"]
    assert len(trace["enforcement_path"]) == 3
    assert trace["enforcement_path"][-1]["action"] == "deny"
    assert trace["remediation_hints"][0]["violation_code"] == "ERR_01"
