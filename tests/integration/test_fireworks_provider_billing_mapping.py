"""Tests for Fireworks AI billing mapping — cost estimation, pricing engine integration."""


from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.fireworks_provider import FireworksProvider


class TestProviderCostMapping:
    def test_fireworks_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("fireworks", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_fireworks_direct_estimate_cost(self):
        provider = FireworksProvider()
        cost = provider.estimate_cost("accounts/fireworks/models/llama-v3p1-70b", 1000, 500)
        assert cost == 0.0

    def test_fireworks_estimate_unknown_model(self):
        provider = FireworksProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
