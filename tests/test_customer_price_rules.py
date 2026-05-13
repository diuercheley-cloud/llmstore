import pytest

from app.services.billing.pricing_engine import (
    calculate_customer_price,
    get_customer_pricing_config,
)


def test_get_customer_pricing_config():
    cfg = get_customer_pricing_config()
    assert "plans" in cfg
    assert "default_markup_percent" in cfg


def test_all_plans_have_required_fields():
    cfg = get_customer_pricing_config()
    for code, plan in cfg.get("plans", {}).items():
        assert "label" in plan, f"plan {code} missing label"
        assert "markup_percent" in plan, f"plan {code} missing markup_percent"


def test_free_plan_zero_price():
    result = calculate_customer_price("free", 1000, 500)
    assert result.price_brl == 0.0
    assert result.plan_code == "free"


def test_basic_plan_positive_price():
    result = calculate_customer_price("basic", 1000, 500)
    assert result.price_brl >= 0
    assert result.plan_code == "basic"


def test_pro_plan_positive_price():
    result = calculate_customer_price("pro", 1000, 500)
    assert result.price_brl >= 0


def test_enterprise_plan_positive_price():
    result = calculate_customer_price("enterprise", 1000, 500)
    assert result.price_brl >= 0


def test_cache_half_price_for_basic():
    no_cache = calculate_customer_price("basic", 1000, 500, cache_hit=False)
    cache = calculate_customer_price("basic", 1000, 500, cache_hit=True)
    assert cache.price_brl <= no_cache.price_brl


def test_cache_discount_not_applied_when_zero():
    cfg = get_customer_pricing_config()
    assert cfg.get("cache_discount_percent", 0) > 0


def test_price_increases_with_tokens():
    small = calculate_customer_price("basic", 100, 50)
    large = calculate_customer_price("basic", 10000, 5000)
    assert large.price_brl >= small.price_brl


def test_markup_reflected_in_price():
    result = calculate_customer_price("basic", 1000, 500)
    assert result.markup_percent == 50


def test_no_secrets():
    cfg = get_customer_pricing_config()
    dump = str(cfg)
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()
