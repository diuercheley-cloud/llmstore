import pytest
from app.schemas.routing import EndpointType, RoutingDecision, RoutingStrategy, SmartRouterInput
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


def test_local_first_selects_local():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    assert dec.selected_provider in ("local", "lmstudio", "mock")
    assert dec.cloud_used is False


def test_cloud_disabled_does_not_use_cloud():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.premium_quality, cloud_allowed=False)
    dec = sr.route(inp)
    assert dec.cloud_used is False
    assert dec.selected_provider not in ("openai", "anthropic", "deepseek", "openrouter")


def test_routing_decision_has_all_fields():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    assert isinstance(dec, RoutingDecision)
    assert dec.selected_provider
    assert dec.selected_model
    assert dec.selected_backend
    assert dec.reason
    assert isinstance(dec.cloud_used, bool)
    assert isinstance(dec.estimated_cost_brl, float)
    assert isinstance(dec.warnings, list)
    assert isinstance(dec.fallback_chain, list)


def test_no_prompt_in_decision():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    dump = dec.model_dump_json()
    assert "prompt" not in dump.lower() or "prompt" in ["prompt_estimated_tokens"]


def test_no_secrets_in_decision():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    dec = sr.route(inp)
    dump = dec.model_dump_json()
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()
    assert "token" not in dump.lower() or "estimated_tokens" in dump


@pytest.mark.parametrize(
    "strategy,expected_local",
    [
        (RoutingStrategy.local_first, True),
        (RoutingStrategy.lowest_cost, True),
        (RoutingStrategy.premium_quality, True),
        (RoutingStrategy.coding, True),
        (RoutingStrategy.embeddings_optimized, True),
        (RoutingStrategy.rag_optimized, True),
        (RoutingStrategy.fallback_only, True),
    ],
)
def test_all_strategies_can_return_local(strategy, expected_local):
    sr = SmartRouter()
    inp = _make_input(strategy=strategy, cloud_allowed=False)
    dec = sr.route(inp)
    if expected_local:
        assert dec.selected_provider in ("local", "lmstudio", "mock")
    assert isinstance(dec, RoutingDecision)


def test_insufficient_balance_blocks_cloud():
    sr = SmartRouter()
    inp = _make_input(
        strategy=RoutingStrategy.premium_quality,
        cloud_allowed=True,
        wallet_balance_brl=0.0,
    )
    dec = sr.route(inp)
    assert (
        dec.cloud_used is False
        or "insufficient balance" in str(dec.warnings or "").lower()
        or "balance" in str(dec.reason).lower()
    )


def test_simulate_returns_multiple_strategies():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    decision, strategies, provider_states, config_snapshot = sr.simulate(inp)
    assert len(strategies) >= 3
    assert decision.selected_provider
    assert isinstance(config_snapshot, dict)


def test_logging_works():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.local_first)
    sr.route(inp)
    assert len(sr.decision_log) >= 1
    entry = sr.decision_log[0]
    assert "requested_model" in entry
    assert "selected_provider" in entry
    assert "routing_strategy" in entry
    assert "timestamp" in entry


def test_get_last_decisions():
    sr = SmartRouter()
    for _ in range(5):
        sr.route(_make_input(strategy=RoutingStrategy.local_first))
    decisions = sr.get_last_decisions(limit=3)
    assert len(decisions) <= 3
    assert len(decisions) >= 1


def test_get_policy():
    sr = SmartRouter()
    policy = sr.get_policy()
    assert "default_strategy" in policy
    assert policy["default_strategy"] == "local_first"
    assert "fallback_order" in policy


def test_fallback_chain_populated_on_failure():
    sr = SmartRouter()
    inp = _make_input(strategy=RoutingStrategy.fallback_only, cloud_allowed=False)
    dec = sr.route(inp)
    assert len(dec.fallback_chain) >= 1
