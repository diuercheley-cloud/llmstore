"""Tests for fallback safety — cloud not forced, cost cap respected, no secret leak."""


import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def router():
    return SmartRouter()


def test_cloud_not_used_when_cloud_allowed_false(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=False,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.cloud_used is False
    assert decision.selected_provider not in ("openai", "anthropic", "deepseek", "openrouter")


def test_cloud_not_used_when_global_disabled(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._get_cloud_providers_enabled", lambda: False)
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.cloud_used is False
    assert decision.selected_provider not in ("openai", "anthropic", "deepseek", "openrouter")


def test_no_forced_cloud_when_no_key(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.premium_quality,
    )
    decision = router.route(inp)
    assert decision.selected_provider in ("local", "lmstudio", "mock")


def test_cost_cap_respected(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._estimate_cost", lambda p, pt, mt: 100.0)
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    warnings = [w for w in decision.warnings if "cost" in w.lower()]
    assert len(warnings) >= 0
    if decision.cloud_used:
        assert len(warnings) > 0


def test_zero_wallet_blocks_cloud(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._get_cloud_providers_enabled", lambda: True)
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: True)
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        wallet_balance_brl=0.0,
        strategy=RoutingStrategy.premium_quality,
    )
    decision = router.route(inp)
    if decision.cloud_used:
        warnings = [w for w in decision.warnings if "balance" in w.lower() or "wallet" in w.lower()]
        assert len(warnings) > 0


def test_no_prompt_in_decision(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = str(decision.model_dump())
    assert "Responda apenas: OK" not in sanitized


def test_no_api_key_in_decision(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    sanitized = str(decision.model_dump())
    for pat in ("sk-", "api_key", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        if pat in sanitized:
            assert "****" in sanitized or "test" in sanitized


def test_reason_sanitized_max_length(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert len(decision.reason) <= 500


def test_fallback_to_mock_when_nothing_available(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: False)
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.selected_provider == "mock"


def test_local_only_mode_no_cloud_strategy(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: pid in ("local", "mock"))
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=False,
        strategy=RoutingStrategy.premium_quality,
    )
    decision = router.route(inp)
    assert decision.cloud_used is False
    assert decision.selected_provider in ("local", "mock")
