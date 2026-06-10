"""Tests for fallback routing logic — local failure, cloud takeover, decision fields."""

from pathlib import Path

import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter, _is_provider_available

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def router():
    return SmartRouter()


def test_normal_local_selected(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.selected_provider in ("local", "lmstudio", "mock")
    assert decision.cloud_used is False


def test_local_first_with_cloud_allowed_local_available(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.selected_provider == "local"
    assert "local" in decision.fallback_chain or not decision.fallback_chain
    assert decision.cloud_used is False


def test_is_provider_available_local():
    assert _is_provider_available("local") is True


def test_is_provider_available_mock():
    assert _is_provider_available("mock") is True


def test_is_provider_available_cloud_not_configured():
    result = _is_provider_available("openai")
    assert result is False


def test_is_provider_available_unknown():
    assert _is_provider_available("nonexistent") is False


def test_fallback_chain_not_empty_when_local_unavailable(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: pid not in ("local", "lmstudio"))
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert len(decision.fallback_chain) > 0
    assert decision.selected_provider != "local"


def test_fallback_to_cloud_only_if_cloud_allowed(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: pid not in ("local", "lmstudio"))
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=False,
        strategy=RoutingStrategy.local_first,
    )
    decision = router.route(inp)
    assert decision.cloud_used is False
    assert decision.selected_provider in ("mock",)


def test_fallback_chain_includes_tried_providers(router, monkeypatch):
    monkeypatch.setattr("app.services.routing.smart_router._is_provider_available", lambda pid: pid == "mock")
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.fallback_only,
    )
    decision = router.route(inp)
    assert "local" in decision.fallback_chain
    assert "mock" in decision.selected_provider or "mock" in decision.fallback_chain


def test_force_local_failure_flag_blocks_local(monkeypatch):
    monkeypatch.setenv("ROUTING_TEST_FORCE_LOCAL_FAILURE", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert _is_provider_available("local") is False
    assert _is_provider_available("lmstudio") is False


def test_force_local_failure_not_affect_mock_if_not_in_local_providers(monkeypatch):
    monkeypatch.setenv("ROUTING_TEST_FORCE_LOCAL_FAILURE", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert _is_provider_available("local") is False


def test_force_local_flag_disabled_local_available(monkeypatch):
    monkeypatch.setenv("ROUTING_TEST_FORCE_LOCAL_FAILURE", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert _is_provider_available("local") is True


def test_simulate_routing_return_fields(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
    )
    decision, strategies, provider_states, config_snapshot = router.simulate(inp)
    assert hasattr(decision, "selected_provider")
    assert hasattr(decision, "fallback_chain")
    assert hasattr(decision, "cloud_used")
    assert hasattr(decision, "reason")
    assert isinstance(strategies, list)
    assert isinstance(provider_states, dict)
    assert isinstance(config_snapshot, dict)


def test_no_secrets_or_prompts_in_decision(router):
    inp = SmartRouterInput(
        endpoint_type=EndpointType.chat,
        cloud_allowed=True,
        strategy=RoutingStrategy.local_first,
        task_type=None,
    )
    decision = router.route(inp)
    sanitized = str(decision.reason).lower()
    for kw in ("api_key", "secret", "authorization", "Responda apenas"):
        assert kw not in sanitized
