"""Tests for Perplexity billing mapping — cost estimation, pricing engine integration."""

import pytest

from app.services.billing.pricing_engine import estimate_provider_cost
from app.services.providers.perplexity_provider import PerplexityProvider


class TestProviderCostMapping:
    def test_perplexity_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("perplexity", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_perplexity_direct_estimate_cost(self):
        provider = PerplexityProvider()
        cost = provider.estimate_cost("sonar-pro", 1000, 500)
        assert cost == 0.0

    def test_perplexity_estimate_unknown_model(self):
        provider = PerplexityProvider()
        assert provider.estimate_cost("unknown", 100, 50) == 0.0
