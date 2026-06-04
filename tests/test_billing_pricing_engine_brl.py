import os

from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_financials,
    calculate_margin,
    convert_usd_to_brl,
    estimate_provider_cost,
    get_fx_rate,
)


def test_fx_rate_default():
    rate, source = get_fx_rate()
    assert rate == 5.00
    assert source == "manual_env"


def test_fx_rate_from_env(monkeypatch):
    monkeypatch.setenv("USD_BRL_RATE", "4.95")
    rate, source = get_fx_rate()
    assert rate == 4.95


def test_estimate_provider_cost_local():
    result = estimate_provider_cost("local", 1000, 500)
    assert result.cost_usd == 0.0
    assert result.cost_brl == 0.0
    assert result.pricing_configured is True
    assert result.fx_rate == 5.0


def test_estimate_provider_cost_openai_not_configured():
    result = estimate_provider_cost("openai", 1000, 500)
    assert result.cost_usd == 0.0
    assert result.pricing_configured is False


def test_estimate_provider_cost_unknown():
    result = estimate_provider_cost("nonexistent", 1000, 500)
    assert result.cost_usd == 0.0
    assert result.pricing_configured is False


def test_estimate_provider_cost_pricing_configured(monkeypatch):
    monkeypatch.setenv("USD_BRL_RATE", "5.00")
    pricing = {
        "fx_rate_brl_per_usd": 5.0,
        "providers": {
            "openai": {
                "cost_usd_per_1k_prompt": 0.0025,
                "cost_usd_per_1k_completion": 0.01,
                "pricing_configured": True,
            }
        },
    }
    import json
    import pathlib
    import tempfile

    from app.services.billing import pricing_engine
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(pricing, tmp)
    tmp.close()
    orig = pricing_engine._PROVIDER_PRICING_PATH
    pricing_engine._PROVIDER_PRICING_PATH = pathlib.Path(tmp.name)
    try:
        result = pricing_engine.estimate_provider_cost("openai", 1000, 500)
        assert result.cost_usd > 0
        assert result.pricing_configured is True
        assert result.cost_brl == result.cost_usd * 5.0
    finally:
        pricing_engine._PROVIDER_PRICING_PATH = orig
        os.unlink(tmp.name)


def test_calculate_customer_price_basic():
    result = calculate_customer_price("basic", 1000, 500)
    assert result.price_brl > 0
    assert result.plan_code == "basic"
    assert result.markup_percent == 50


def test_calculate_customer_price_free():
    result = calculate_customer_price("free", 1000, 500)
    assert result.price_brl == 0.0
    assert result.plan_code == "free"


def test_calculate_customer_price_unknown_plan():
    result = calculate_customer_price("unknown", 1000, 500)
    assert result.price_brl == 0.0


def test_calculate_customer_price_cache_hit():
    result_no_cache = calculate_customer_price("basic", 1000, 500, cache_hit=False)
    result_cache = calculate_customer_price("basic", 1000, 500, cache_hit=True)
    assert result_cache.price_brl <= result_no_cache.price_brl


def test_calculate_margin():
    margin = calculate_margin(0.005, 0.01)
    assert margin.gross_profit_brl == 0.005
    assert margin.margin_percent == 50.0


def test_calculate_margin_zero_price():
    margin = calculate_margin(0.0, 0.0)
    assert margin.gross_profit_brl == 0.0
    assert margin.margin_percent is None


def test_convert_usd_to_brl():
    brl, rate, source = convert_usd_to_brl(1.0)
    assert brl == 5.0
    assert rate == 5.0
    assert source == "manual_env"


def test_convert_usd_to_brl_custom_rate():
    brl, rate, source = convert_usd_to_brl(1.0, fx_rate=4.50)
    assert brl == 4.50


def test_calculate_financials():
    result = calculate_financials(
        provider="local",
        prompt_tokens=1000,
        completion_tokens=500,
        cache_hit=False,
        plan_code="basic",
    )
    assert result["provider"] == "local"
    assert result["prompt_tokens"] == 1000
    assert result["completion_tokens"] == 500
    assert result["total_tokens"] == 1500
    assert "provider_cost_usd" in result
    assert "provider_cost_brl" in result
    assert "customer_price_brl" in result
    assert "gross_profit_brl" in result
    assert "margin_percent" in result or result["margin_percent"] is None
    assert result["fx_rate"] == 5.0
    assert result["fx_rate_source"] == "manual_env"


def test_calculate_financials_no_secrets():
    result = calculate_financials("local", 100, 50)
    dump = str(result)
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()


def test_no_external_calls():
    result = calculate_financials("local", 100, 50, plan_code="free")
    assert result["customer_price_brl"] == 0.0
    assert result["provider_cost_brl"] == 0.0
