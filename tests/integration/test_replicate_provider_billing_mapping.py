"""Tests for Replicate billing mapping — cost estimation, pricing engine integration."""


from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.replicate_provider import ReplicateProvider


class TestProviderCostMapping:
    def test_replicate_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("replicate", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_replicate_direct_estimate_cost(self):
        provider = ReplicateProvider()
        cost = provider.estimate_cost("meta/meta-llama-3-70b", 1000, 500)
        assert cost == 0.0

    def test_replicate_estimate_unknown_model(self):
        provider = ReplicateProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
