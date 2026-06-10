from app.services.governance.policy_engine.policy_evaluator import evaluate_policy
from app.services.governance.policy_engine.receipts import build_policy_receipt


def test_phase_82_governance_core_decision_and_receipt():
    policy = {
        "rules": [
            {"name": "approval-prod", "action": "require_approval_if", "conditions": [{"field": "env", "operator": "eq", "value": "prod"}]}
        ]
    }
    result = evaluate_policy(policy, {"env": "prod"})
    assert result["decision"] == "require_approval"
    receipt = build_policy_receipt("policy-1", result["decision"], "deployment-1")
    assert receipt["receipt_type"] == "deterministic_policy_evaluation"
