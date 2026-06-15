"""Tests for Groq billing mapping — cost estimation, pricing engine integration."""

from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.groq_provider import GroqProvider


class TestProviderCostMapping:
    def test_groq_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("groq", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_groq_direct_estimate_cost(self):
        provider = GroqProvider()
        cost = provider.estimate_cost("llama-3.1-70b", 1000, 500)
        assert cost == 0.0

    def test_groq_estimate_unknown_model(self):
        provider = GroqProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
