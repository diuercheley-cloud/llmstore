import pytest
from app.services.governance.policy_engine.policy_parser import parse_policy_dsl


def test_parse_policy_dsl_normalizes_and_sorts_rules():
    parsed = parse_policy_dsl(
        {
            "rules": [
                {
                    "name": "b",
                    "action": "warn_if",
                    "priority": 1,
                    "conditions": [{"field": "severity", "operator": "eq", "value": "low"}],
                },
                {
                    "name": "a",
                    "action": "block_if",
                    "priority": 10,
                    "conditions": [{"field": "severity", "operator": "eq", "value": "high"}],
                },
            ]
        }
    )
    assert parsed["rules"][0]["name"] == "a"


def test_parse_policy_dsl_rejects_invalid_action():
    with pytest.raises(ValueError):
        parse_policy_dsl(
            {
                "rules": [
                    {
                        "action": "exec_if",
                        "conditions": [{"field": "x", "operator": "eq", "value": 1}],
                    }
                ]
            }
        )
