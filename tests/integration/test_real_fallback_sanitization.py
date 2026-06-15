"""Tests for fallback sanitization — no secret leak, no prompt leak, no key in artifacts."""

import json
import re

import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


KEY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"OPENAI_API_KEY=[^\s]"),
    re.compile(r"ANTHROPIC_API_KEY=[^\s]"),
    re.compile(r"DEEPSEEK_API_KEY=[^\s]"),
    re.compile(r"Bearer sk-[a-zA-Z0-9][a-zA-Z0-9._-]+"),
]


def test_no_key_in_routing_decision():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = json.dumps(decision.model_dump())
    for pat in KEY_PATTERNS:
        assert not pat.search(sanitized), f"Key pattern found in routing decision: {pat}"


def test_no_key_in_simulate():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision, strategies, states, snapshot = router.simulate(inp)
    sanitized = json.dumps(
        {
            "decision": decision.model_dump(),
            "strategies": strategies,
            "states": states,
            "snapshot": snapshot,
        }
    )
    for pat in KEY_PATTERNS:
        assert not pat.search(sanitized), f"Key pattern found in simulate: {pat}"


def test_no_key_in_logged_decisions():
    router = SmartRouter()
    for _ in range(3):
        inp = SmartRouterInput(
            endpoint_type=EndpointType.chat,
            cloud_allowed=True,
            strategy=RoutingStrategy.local_first,
        )
        router.route(inp)
    decisions = router.get_last_decisions(limit=10)
    sanitized = json.dumps(decisions)
    for pat in KEY_PATTERNS:
        assert not pat.search(sanitized), f"Key pattern found in logged decisions: {pat}"


def test_no_prompt_in_decision():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = str(decision.model_dump())
    assert "Responda apenas: OK" not in sanitized


def test_no_secrets_in_policy():
    router = SmartRouter()
    policy = router.get_policy()
    sanitized = json.dumps(policy)
    for pat in KEY_PATTERNS:
        assert not pat.search(sanitized), f"Key pattern found in policy: {pat}"


def test_reason_sanitized():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert "\n" not in decision.reason
    assert "\r" not in decision.reason
    assert len(decision.reason) <= 500


def test_force_failure_flag_not_leaked():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = str(decision.model_dump())
    assert "ROUTING_TEST_FORCE_LOCAL_FAILURE" not in sanitized


def test_wallet_balance_not_leaked():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        wallet_balance_brl=100.0,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = str(decision.model_dump())
    assert "wallet_balance_brl" not in sanitized


def test_fallback_chain_does_not_leak_creds():
    router = SmartRouter()
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    chain_str = " ".join(decision.fallback_chain)
    for kw in ("sk-", "api_key", "token"):
        assert kw not in chain_str
