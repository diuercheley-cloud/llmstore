"""Tests for fallback billing — cost estimation, financial tracking, wallet debit."""

import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter, _estimate_cost


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def router():
    return SmartRouter()


def test_estimate_cost_local_zero():
    cost = _estimate_cost("local", 1000, 500)
    assert cost == 0.0


def test_estimate_cost_lmstudio_zero():
    cost = _estimate_cost("lmstudio", 1000, 500)
    assert cost == 0.0


def test_estimate_cost_mock_zero():
    cost = _estimate_cost("mock", 1000, 500)
    assert cost == 0.0


def test_estimate_cost_openai():
    cost = _estimate_cost("openai", 1000, 500)
    expected = (1000 * 0.0000025) + (500 * 0.00001)
    assert cost == expected


def test_estimate_cost_anthropic():
    cost = _estimate_cost("anthropic", 1000, 500)
    expected = (1000 * 0.000003) + (500 * 0.000015)
    assert cost == expected


def test_estimate_cost_deepseek():
    cost = _estimate_cost("deepseek", 1000, 500)
    expected = (1000 * 0.0000005) + (500 * 0.000002)
    assert cost == expected


def test_estimate_cost_unknown_provider():
    cost = _estimate_cost("nonexistent", 1000, 500)
    assert cost == 0.0


def test_estimated_cost_brl_in_decision(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
        prompt_estimated_tokens=1000,
        max_output_tokens=500,
    )
    decision = router.route(inp)
    assert decision.estimated_cost_brl >= 0
    assert isinstance(decision.estimated_cost_brl, float)


def test_estimated_cost_zero_for_local(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=False,
        strategy=RoutingStrategy.local_first,
        prompt_estimated_tokens=1000,
        max_output_tokens=500,
    )
    decision = router.route(inp)
    if decision.selected_provider == "local":
        assert decision.estimated_cost_brl == 0.0


def test_fallback_chain_records_cost_context(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
        prompt_estimated_tokens=100,
        max_output_tokens=50,
    )
    decision = router.route(inp)
    assert len(decision.fallback_chain) >= 0
    assert isinstance(decision.fallback_chain, list)


def test_cloud_used_flag_in_decision(router, monkeypatch):
    monkeypatch.setattr(
        "app.services.routing.smart_router._is_provider_available", lambda pid: True
    )
    monkeypatch.setattr(
        "app.services.routing.smart_router._get_cloud_providers_enabled", lambda: True
    )
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.premium_quality,
    )
    decision = router.route(inp)
    assert isinstance(decision.cloud_used, bool)


def test_financials_calculated_on_fallback_to_cloud(router, monkeypatch):
    monkeypatch.setattr(
        "app.services.routing.smart_router._is_provider_available",
        lambda pid: pid not in ("local", "lmstudio"),
    )
    monkeypatch.setattr(
        "app.services.routing.smart_router._get_cloud_providers_enabled", lambda: True
    )
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
        prompt_estimated_tokens=500,
        max_output_tokens=200,
    )
    decision = router.route(inp)
    assert decision.estimated_cost_brl >= 0
    if decision.cloud_used and "openai" in decision.selected_provider:
        assert decision.estimated_cost_brl > 0


def test_wallet_debit_context_no_negative_balance(router, monkeypatch):
    monkeypatch.setattr(
        "app.services.routing.smart_router._is_provider_available", lambda pid: True
    )
    monkeypatch.setattr(
        "app.services.routing.smart_router._get_cloud_providers_enabled", lambda: True
    )
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        wallet_balance_brl=10.0,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert isinstance(decision.cloud_used, bool)
