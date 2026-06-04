
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


def test_default_strategy_is_local_first():
    sr = SmartRouter()
    assert sr.default_strategy == "local_first"


def test_policy_has_expected_keys():
    sr = SmartRouter()
    policy = sr.get_policy()
    assert "default_strategy" in policy
    assert "allow_cloud_fallback" in policy
    assert "complexity_threshold" in policy
    assert "coding_provider_preference" in policy
    assert "low_budget_provider_preference" in policy
    assert "premium_provider_preference" in policy
    assert "max_provider_cost_per_request_brl" in policy
    assert "tenant_policy_overrides" in policy
    assert "fallback_order" in policy


def test_policy_has_correct_default_values():
    sr = SmartRouter()
    policy = sr.get_policy()
    assert policy["default_strategy"] == "local_first"
    assert policy["allow_cloud_fallback"] is False
    assert policy["complexity_threshold"] == 4000
    assert policy["coding_provider_preference"] == "anthropic"
    assert policy["low_budget_provider_preference"] == "deepseek"
    assert policy["premium_provider_preference"] == "openai"
    assert policy["max_provider_cost_per_request_brl"] == 0.50
    assert isinstance(policy["tenant_policy_overrides"], dict)
    assert policy["fallback_order"] == ["local", "lmstudio", "mock"]


def test_tenant_policy_overrides_empty_by_default():
    sr = SmartRouter()
    policy = sr.get_policy()
    assert policy["tenant_policy_overrides"] == {}


def test_fallback_order_includes_local_only():
    sr = SmartRouter()
    policy = sr.get_policy()
    fallback = policy["fallback_order"]
    assert "local" in fallback
    assert "mock" in fallback
    for provider in fallback:
        assert provider not in ("openai", "anthropic", "deepseek", "openrouter")


def test_strategy_enum_values():
    assert RoutingStrategy.local_first.value == "local_first"
    assert RoutingStrategy.lowest_cost.value == "lowest_cost"
    assert RoutingStrategy.premium_quality.value == "premium_quality"
    assert RoutingStrategy.coding.value == "coding"
    assert RoutingStrategy.embeddings_optimized.value == "embeddings_optimized"
    assert RoutingStrategy.rag_optimized.value == "rag_optimized"
    assert RoutingStrategy.fallback_only.value == "fallback_only"


def test_endpoint_type_enum_values():
    assert EndpointType.chat.value == "chat"
    assert EndpointType.responses.value == "responses"
    assert EndpointType.embeddings.value == "embeddings"
    assert EndpointType.rag.value == "rag"
    assert EndpointType.tts.value == "tts"


def test_all_strategies_resolve():
    sr = SmartRouter()
    for strategy in RoutingStrategy:
        inp = _make_input(strategy=strategy, cloud_allowed=False)
        dec = sr.route(inp)
        assert dec.selected_provider
        assert dec.reason


def test_coding_strategy_falls_back_when_cloud_disabled():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.coding, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.cloud_used is False
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_premium_strategy_falls_back_when_cloud_disabled():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.premium_quality, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.cloud_used is False
    assert dec.selected_provider in ("local", "lmstudio", "mock")


def test_lowest_cost_strategy_with_disabled_cloud():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.lowest_cost, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.cloud_used is False
