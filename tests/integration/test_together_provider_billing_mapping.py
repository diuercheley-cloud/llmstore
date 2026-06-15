"""Tests for Together AI billing mapping — cost estimation, pricing engine integration."""

from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.together_provider import TogetherProvider


class TestProviderCostMapping:
    def test_together_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("together", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_together_direct_estimate_cost(self):
        provider = TogetherProvider()
        cost = provider.estimate_cost("mistralai/Mixtral-8x7B-Instruct-v0.1", 1000, 500)
        assert cost == 0.0

    def test_together_estimate_unknown_model(self):
        provider = TogetherProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
