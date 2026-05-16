from app.services.governance.policy_engine.policy_conflict_resolver import detect_policy_conflicts, resolve_decision
from app.services.governance.policy_engine.policy_parser import parse_policy_dsl


def _matches(operator: str, actual, expected) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    if operator == "contains":
        return expected in actual
    if operator == "exists":
        return (actual is not None) is bool(expected)
    return False


def evaluate_policy(policy_dsl: dict, subject: dict) -> dict:
    conflicts = detect_policy_conflicts(policy_dsl)
    if conflicts:
        return {
            "evaluation_status": "blocked",
            "decision": "blocked",
            "explanation": "critical policy conflict detected",
            "matched_rules": [],
            "replay_safe": True,
            "conflicts": conflicts,
        }
    parsed = parse_policy_dsl(policy_dsl)
    matched_rules: list[dict] = []
    actions: list[str] = []
    for rule in parsed["rules"]:
        if all(_matches(item["operator"], subject.get(item["field"]), item.get("value")) for item in rule["conditions"]):
            matched_rules.append(rule)
            actions.append(rule["action"])
    decision = resolve_decision(actions)
    status = "evaluated" if matched_rules else "no_match"
    explanation = f"matched {len(matched_rules)} rule(s)" if matched_rules else "no policy rules matched"
    return {
        "evaluation_status": status,
        "decision": decision,
        "explanation": explanation,
        "matched_rules": matched_rules,
        "replay_safe": True,
        "conflicts": [],
    }

