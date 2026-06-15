from app.services.governance.policy_engine.policy_evaluator import evaluate_policy


def verify_replay(policy_dsl: dict, subject: dict, expected_decision: str) -> dict:
    result = evaluate_policy(policy_dsl, subject)
    return {
        "verification_status": "passed" if result["decision"] == expected_decision else "failed",
        "decision": result["decision"],
        "replay_safe": result["replay_safe"],
    }
