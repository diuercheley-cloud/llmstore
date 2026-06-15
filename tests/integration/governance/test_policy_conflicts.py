from app.services.governance.policy_engine.policy_conflict_resolver import detect_policy_conflicts
from app.services.governance.policy_engine.policy_evaluator import evaluate_policy


def test_policy_conflicts_detect_allow_vs_block():
    policy = {
        "rules": [
            {
                "name": "allow-prod",
                "action": "allow_if",
                "conditions": [{"field": "env", "operator": "eq", "value": "prod"}],
            },
            {
                "name": "block-prod",
                "action": "block_if",
                "conditions": [{"field": "env", "operator": "eq", "value": "prod"}],
            },
        ]
    }
    conflicts = detect_policy_conflicts(policy)
    assert conflicts
    result = evaluate_policy(policy, {"env": "prod"})
    assert result["decision"] == "blocked"
