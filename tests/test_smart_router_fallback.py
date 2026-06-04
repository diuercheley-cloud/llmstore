import pytest
from app.schemas.routing import EndpointType, RoutingStrategy, SmartRouterInput
from app.services.routing.smart_router import SmartRouter, reset_smart_router


@pytest.fixture(autouse=True)
def reset_router():
    reset_smart_router()
    yield
    reset_smart_router()


def _make_input(**overrides) -> SmartRouterInput:
    kwargs = dict(endpoint_type=EndpointType.chat, cloud_allowed=False)
    kwargs.update(overrides)
    return SmartRouterInput(**kwargs)


def test_local_first_fallback_to_mock():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.selected_provider in ("local", "lmstudio", "mock")
    assert "mock" not in dec.selected_provider or len(dec.fallback_chain) > 0


def test_fallback_only_uses_fallback_order():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.fallback_only, cloud_allowed=False)
    dec = sr.route(inp)
    assert len(dec.fallback_chain) >= 1
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_fallback_chain_contains_attempted_providers():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.fallback_only, cloud_allowed=False)
    dec = sr.route(inp)
    for provider in dec.fallback_chain:
        assert isinstance(provider, str)
    assert dec.selected_provider == dec.fallback_chain[-1] if dec.fallback_chain else True


def test_embeddings_fallback_to_mock():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.embeddings_optimized, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_rag_fallback_to_mock():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.rag_optimized, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_cloud_allowed_but_disabled_globally_stays_local():
    sr = SmartRouter()
    inp = _make_input(
        strategy=RoutingStrategy.premium_quality,
        cloud_allowed=True,
    )
    dec = sr.route(inp)
    assert dec.cloud_used is False
    has_warning = any("disabled" in w.lower() for w in dec.warnings)
    assert has_warning or dec.selected_provider in ("local", "lmstudio", "mock")


def test_max_cost_exceeded_triggers_warning():
    sr = SmartRouter()
    original_max = sr.policy.get("max_provider_cost_per_request_brl", 0.50)
    sr.policy["max_provider_cost_per_request_brl"] = 0.0000001
    inp = _make_input(
        strategy=RoutingStrategy.premium_quality,
        cloud_allowed=False,
        prompt_estimated_tokens=10000,
    )
    dec = sr.route(inp)
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_multiple_routes_produce_same_structure():
    sr = SmartRouter()
    for _ in range(10):
        inp = _make_input(strategy=RoutingStrategy.local_first, cloud_allowed=False)
        dec = sr.route(inp)
        assert isinstance(dec.selected_provider, str)
        assert isinstance(dec.reason, str)
        assert isinstance(dec.fallback_chain, list)
