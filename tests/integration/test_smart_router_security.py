import json

import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter, _sanitize_reason, reset_smart_router


@pytest.fixture(autouse=True)
def reset_router():
    reset_smart_router()
    yield
    reset_smart_router()


def _make_input(**overrides) -> SmartRouterInput:
    kwargs = dict(endpoint_type=EndpointType.chat, cloud_allowed=False)
    kwargs.update(overrides)
    return SmartRouterInput(**kwargs)


def test_decision_does_not_contain_prompt_text():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    serialized = dec.model_dump_json()
    assert "user_message" not in serialized.lower()
    assert "system_prompt" not in serialized.lower()


def test_decision_does_not_expose_api_keys():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    serialized = dec.model_dump_json()
    assert "sk-" not in serialized
    assert "api_key" not in serialized.lower()
    assert "x-api-key" not in serialized.lower()


def test_decision_does_not_expose_secrets():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    serialized = dec.model_dump_json()
    assert "secret" not in serialized.lower()


def test_decision_reason_is_sanitized():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    assert len(dec.reason) <= 500
    assert "\n" not in dec.reason


def test_sanitize_removes_newlines():
    result = _sanitize_reason("line1\nline2\rline3")
    assert "\n" not in result
    assert "\r" not in result


def test_sanitize_truncates_long_strings():
    long = "x" * 1000
    result = _sanitize_reason(long)
    assert len(result) <= 500


def test_sanitize_redacts_sensitive_keywords():
    result = _sanitize_reason("my api_key is secret and token=abc")
    assert "api_key" not in result
    assert "secret" not in result
    assert "token" not in result or result == "token"


def test_sanitize_handles_none():
    result = _sanitize_reason("normal reason")
    assert result == "normal reason"


def test_log_does_not_contain_raw_prompt():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    sr.route(inp)
    for entry in sr.decision_log:
        assert (
            "prompt" not in str(entry).lower()
            or "prompt_estimated_tokens" in str(entry)
            or "routing_strategy" in str(entry)
        )
        assert "api_key" not in str(entry).lower()
        assert "secret" not in str(entry).lower()


def test_simulation_does_not_leak_sensitive_data():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    decision, strategies, provider_states, config_snapshot = sr.simulate(inp)
    dump = json.dumps(
        {
            "decision": decision.model_dump(),
            "strategies": strategies,
            "config": {k: str(v) for k, v in config_snapshot.items()},
        }
    )
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()
    assert "sk-" not in dump


def test_log_entries_have_sanitized_reason():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    sr.route(inp)
    for entry in sr.decision_log:
        reason = entry.get("sanitized_reason", "")
        assert "\n" not in reason
        assert len(reason) <= 500
