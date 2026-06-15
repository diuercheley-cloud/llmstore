"""Tests for xAI billing mapping — cost estimation, pricing engine integration."""

from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.xai_provider import XAIProvider


class TestProviderCostMapping:
    def test_xai_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("xai", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_xai_direct_estimate_cost(self):
        provider = XAIProvider()
        cost = provider.estimate_cost("grok-2", 1000, 500)
        assert cost == 0.0

    def test_xai_estimate_unknown_model(self):
        provider = XAIProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
