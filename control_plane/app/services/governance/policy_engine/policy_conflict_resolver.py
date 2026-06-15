from app.services.governance.policy_engine.policy_parser import parse_policy_dsl

CRITICAL_ACTIONS = {"block_if", "deny_if"}


def detect_policy_conflicts(policy_dsl: dict) -> list[dict]:
    parsed = parse_policy_dsl(policy_dsl)
    conflicts: list[dict] = []
    seen_by_condition: dict[str, set[str]] = {}
    for rule in parsed["rules"]:
        condition_key = repr(rule["conditions"])
        seen_by_condition.setdefault(condition_key, set()).add(rule["action"])
    for condition_key, actions in seen_by_condition.items():
        if "allow_if" in actions and CRITICAL_ACTIONS.intersection(actions):
            conflicts.append(
                {
                    "conflict_type": "critical_decision_conflict",
                    "resolution_strategy": "block_on_conflict",
                    "resolution_status": "open",
                    "condition_key": condition_key,
                }
            )
    return conflicts


def resolve_decision(actions: list[str]) -> str:
    ordered = [
        "block_if",
        "deny_if",
        "require_approval_if",
        "require_dry_run_if",
        "warn_if",
        "allow_if",
    ]
    for action in ordered:
        if action in actions:
            return action.replace("_if", "")
    return "no_match"
