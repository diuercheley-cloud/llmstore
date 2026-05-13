"""Tests for OpenAI billing BRL mapping — cost estimation, pricing engine integration."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_financials,
    calculate_margin,
    estimate_provider_cost,
    get_fx_rate,
)
from app.services.providers.openai_provider import OpenAIProvider


class TestProviderCostMapping:
    def test_openai_estimate_provider_cost_not_configured_by_default(self):
        result = estimate_provider_cost("openai", 1000, 500)
        assert result.pricing_configured is False
        assert result.cost_usd == 0.0

    def test_openai_direct_estimate_cost(self):
        provider = OpenAIProvider()
        cost = provider.estimate_cost("gpt-4o-mini", 1000, 500)
        expected = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.60)
        assert cost == expected

    def test_openai_estimate_gpt4o(self):
        provider = OpenAIProvider()
        cost = provider.estimate_cost("gpt-4o", 100, 50)
        expected = (100 / 1_000_000 * 2.50) + (50 / 1_000_000 * 10.00)
        assert cost == expected

    def test_openai_estimate_unknown_model(self):
        provider = OpenAIProvider()
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

    def test_calculate_financials_openai(self):
        result = calculate_financials(
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert result["provider"] == "openai"
        assert result["total_tokens"] == 1500
        assert "provider_cost_usd" in result
        assert "customer_price_brl" in result
        assert "margin_percent" in result


class TestProviderBillingIntegration:
    def test_openai_estimate_cost_matches_pricing_engine_shape(self):
        prov_cost = estimate_provider_cost("openai", 500, 200)
        direct = OpenAIProvider().estimate_cost("gpt-4o-mini", 500, 200)
        assert isinstance(prov_cost.cost_usd, float)
        assert isinstance(direct, float)

    def test_cache_hit_discount_applies(self):
        result_no_cache = calculate_customer_price("basic", 1000, 500, cache_hit=False)
        result_cache = calculate_customer_price("basic", 1000, 500, cache_hit=True)
        assert result_cache.price_brl <= result_no_cache.price_brl

    def test_margin_calculated_correctly(self):
        result = calculate_financials(
            provider="openai",
            prompt_tokens=200,
            completion_tokens=100,
            plan_code="pro",
        )
        assert result["gross_profit_brl"] == round(
            result["customer_price_brl"] - result["provider_cost_brl"], 8
        )

    def test_financials_include_fx_rate(self):
        result = calculate_financials("openai", 100, 50)
        assert result["fx_rate"] > 0
        assert result["fx_rate_source"] == "manual_env"

    def test_embedding_cost_calculation(self):
        provider = OpenAIProvider()
        cost = provider.estimate_cost("text-embedding-3-small", 100, 0)
        expected = (100 / 1_000_000 * 0.02)
        assert cost == expected

    def test_embedding_large_cost(self):
        provider = OpenAIProvider()
        cost = provider.estimate_cost("text-embedding-3-large", 100, 0)
        expected = (100 / 1_000_000 * 0.13)
        assert cost == expected

    def test_pricing_configured_flag(self):
        result = estimate_provider_cost("openai", 100, 50)
        assert isinstance(result.pricing_configured, bool)
