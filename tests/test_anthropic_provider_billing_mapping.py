"""Tests for Anthropic billing BRL mapping — cost estimation, pricing engine integration."""



from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_financials,
    calculate_margin,
    estimate_provider_cost,
    get_fx_rate,
)
from app.services.providers.anthropic_provider import AnthropicProvider


class TestProviderCostMapping:
    def test_anthropic_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("anthropic", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_anthropic_direct_estimate_cost(self):
        provider = AnthropicProvider()
        cost = provider.estimate_cost("claude-3-haiku-20240307", 1000, 500)
        expected = (1000 / 1_000_000 * 0.25) + (500 / 1_000_000 * 1.25)
        assert cost == expected

    def test_anthropic_estimate_sonnet(self):
        provider = AnthropicProvider()
        cost = provider.estimate_cost("claude-3-5-sonnet-20241022", 100, 50)
        expected = (100 / 1_000_000 * 3.00) + (50 / 1_000_000 * 15.00)
        assert cost == expected

    def test_anthropic_estimate_opus(self):
        provider = AnthropicProvider()
        cost = provider.estimate_cost("claude-3-opus-20240229", 100, 50)
        expected = (100 / 1_000_000 * 15.00) + (50 / 1_000_000 * 75.00)
        assert cost == expected

    def test_anthropic_estimate_unknown_model(self):
        provider = AnthropicProvider()
        cost = provider.estimate_cost("unknown", 100, 50)
        assert cost == 0.0

    def test_fx_rate_default(self):
        rate, source = get_fx_rate()
        assert rate > 0
        assert source == "manual_env"

    def test_fx_rate_respects_env(self, monkeypatch):
        monkeypatch.setenv("USD_BRL_RATE", "5.50")
        rate, source = get_fx_rate()
        assert rate == 5.50

    def test_calculate_customer_price_basic_plan(self):
        result = calculate_customer_price(
            plan_code="basic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert result.price_brl >= 0
        assert result.plan_code == "basic"

    def test_calculate_customer_price_no_plan(self):
        result = calculate_customer_price(
            plan_code=None,
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert result.price_brl >= 0
        assert result.plan_code is None

    def test_calculate_margin_positive(self):
        margin = calculate_margin(0.02, 0.10)
        assert margin.gross_profit_brl == 0.08
        assert margin.margin_percent == 80.0

    def test_calculate_margin_zero_cost(self):
        margin = calculate_margin(0.0, 0.10)
        assert margin.gross_profit_brl == 0.10
        assert margin.margin_percent == 100.0

    def test_calculate_margin_zero_price(self):
        margin = calculate_margin(0.02, 0.0)
        assert margin.gross_profit_brl == -0.02
        assert margin.margin_percent is None

    def test_calculate_financials_anthropic(self):
        result = calculate_financials(
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert result["provider"] == "anthropic"
        assert result["total_tokens"] == 1500
        assert "provider_cost_usd" in result
        assert "customer_price_brl" in result
        assert "margin_percent" in result


class TestProviderBillingIntegration:
    def test_anthropic_estimate_cost_matches_pricing_engine_shape(self):
        prov_cost = estimate_provider_cost("anthropic", 500, 200)
        direct = AnthropicProvider().estimate_cost("claude-3-haiku-20240307", 500, 200)
        assert isinstance(prov_cost.cost_usd, float)
        assert isinstance(direct, float)

    def test_cache_hit_discount_applies(self):
        result_no_cache = calculate_customer_price("basic", 1000, 500, cache_hit=False)
        result_cache = calculate_customer_price("basic", 1000, 500, cache_hit=True)
        assert result_cache.price_brl <= result_no_cache.price_brl

    def test_margin_calculated_correctly(self):
        result = calculate_financials(
            provider="anthropic",
            prompt_tokens=200,
            completion_tokens=100,
            plan_code="pro",
        )
        assert result["gross_profit_brl"] == round(
            result["customer_price_brl"] - result["provider_cost_brl"], 8
        )

    def test_financials_include_fx_rate(self):
        result = calculate_financials("anthropic", 100, 50)
        assert result["fx_rate"] > 0
        assert result["fx_rate_source"] == "manual_env"

    def test_pricing_configured_flag(self):
        result = estimate_provider_cost("anthropic", 100, 50)
        assert isinstance(result.pricing_configured, bool)

    def test_anthropic_pricing_coverage(self):
        models = [
            ("claude-3-haiku-20240307", 0.25, 1.25),
            ("claude-3-5-haiku-20241022", 0.80, 4.00),
            ("claude-3-sonnet-20240229", 3.00, 15.00),
            ("claude-3-5-sonnet-20241022", 3.00, 15.00),
            ("claude-3-opus-20240229", 15.00, 75.00),
        ]
        provider = AnthropicProvider()
        for model, prompt_price, completion_price in models:
            cost = provider.estimate_cost(model, 1000, 500)
            expected = (1000 / 1_000_000 * prompt_price) + (500 / 1_000_000 * completion_price)
            assert abs(cost - expected) < 0.0001, f"Pricing mismatch for {model}"
