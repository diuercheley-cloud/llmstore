"""Tests for AI21 Labs billing mapping — cost estimation, pricing engine integration."""

from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.ai21_provider import AI21Provider


class TestProviderCostMapping:
    def test_ai21_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("ai21", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_ai21_direct_estimate_cost(self):
        provider = AI21Provider()
        cost = provider.estimate_cost("jamba-1.5-mini", 1000, 500)
        assert cost == 0.0

    def test_ai21_estimate_unknown_model(self):
        provider = AI21Provider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
