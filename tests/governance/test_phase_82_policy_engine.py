from app.services.governance.policy_engine.policy_evaluator import evaluate_policy
from app.services.governance.policy_engine.policy_replay_verifier import verify_replay


def test_policy_engine_blocks_on_high_risk_subject():
    policy = {
        "rules": [
            {"name": "block-high", "action": "block_if", "priority": 100, "conditions": [{"field": "risk", "operator": "eq", "value": "high"}]},
            {"name": "allow-low", "action": "allow_if", "priority": 10, "conditions": [{"field": "risk", "operator": "eq", "value": "low"}]},
        ]
    }
    result = evaluate_policy(policy, {"risk": "high"})
    assert result["decision"] == "block"
    assert result["evaluation_status"] == "evaluated"


def test_policy_engine_replay_verification_passes():
    policy = {
        "rules": [
            {"name": "dry-run-large", "action": "require_dry_run_if", "priority": 100, "conditions": [{"field": "blast_radius", "operator": "gte", "value": 5}]}
        ]
    }
    verification = verify_replay(policy, {"blast_radius": 9}, "require_dry_run")
    assert verification["verification_status"] == "passed"
