import hashlib
import json


ALLOWED_ACTIONS = {"allow_if", "deny_if", "require_approval_if", "require_dry_run_if", "block_if", "warn_if"}
ALLOWED_OPERATORS = {"eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte", "contains", "exists"}


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def hash_payload(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def parse_policy_dsl(policy_dsl: dict) -> dict:
    if not isinstance(policy_dsl, dict):
        raise ValueError("policy_dsl_must_be_object")
    rules = policy_dsl.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("policy_rules_required")
    normalized_rules: list[dict] = []
    for index, rule in enumerate(rules):
        action = rule.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"invalid_policy_action:{index}")
        conditions = rule.get("conditions", [])
        if not isinstance(conditions, list) or not conditions:
            raise ValueError(f"policy_conditions_required:{index}")
        normalized_conditions = []
        for cond_index, condition in enumerate(conditions):
            operator = condition.get("operator")
            if operator not in ALLOWED_OPERATORS:
                raise ValueError(f"invalid_condition_operator:{index}:{cond_index}")
            normalized_conditions.append(
                {
                    "field": condition["field"],
                    "operator": operator,
                    "value": condition.get("value"),
                }
            )
        normalized_rules.append(
            {
                "name": rule.get("name", f"rule_{index}"),
                "action": action,
                "priority": int(rule.get("priority", 100)),
                "conditions": normalized_conditions,
            }
        )
    normalized_rules.sort(key=lambda item: (-item["priority"], item["name"]))
    return {"version": str(policy_dsl.get("version", "1")), "rules": normalized_rules}

