import json

from scripts.llm_harness.pricing import PricingManager


def test_pricing_manager_default():
    pm = PricingManager()
    
    # Test gpt-4o
    result = pm.calculate_cost("gpt-4o", 1_000_000, 1_000_000)
    assert result is not None
    assert result.cost == 20.0 # 5 + 15
    assert result.known is True
    assert result.currency == "USD"
    
    # Test prefix matching
    result = pm.calculate_cost("gpt-4o-2024-05-13", 1_000_000, 1_000_000)
    assert result is not None
    assert result.cost == 20.0
    
    # Test unknown model
    result = pm.calculate_cost("unknown-model", 100, 100)
    assert result is None

def test_pricing_manager_custom(tmp_path):
    pricing_file = tmp_path / "custom_pricing.json"
    custom_data = {
        "custom-model": {
            "prompt_token_price_per_1m": 1.0,
            "completion_token_price_per_1m": 2.0,
            "currency": "BRL"
        }
    }
    pricing_file.write_text(json.dumps(custom_data))
    
    pm = PricingManager(pricing_file=str(pricing_file))
    result = pm.calculate_cost("custom-model", 1_000_000, 1_000_000)
    assert result is not None
    assert result.cost == 3.0
    assert result.currency == "BRL"
    assert pm.get_currency("custom-model") == "BRL"

def test_pricing_manager_fallback():
    pm = PricingManager()
    # claude-3-5-sonnet-20241022 starts with claude-3-5-sonnet
    # Wait, in DEFAULT_PRICING it's exactly "claude-3-5-sonnet-20241022"
    result = pm.calculate_cost("claude-3-5-sonnet-20241022-v1", 1_000_000, 1_000_000)
    assert result is not None
    assert result.cost == 18.0 # 3 + 15


def test_pricing_manager_unknown_model_does_not_warn(caplog):
    pm = PricingManager()

    with caplog.at_level("WARNING"):
        result = pm.calculate_cost("qwen/qwen3.6-35b-a3b", 100, 100)

    assert result is None
    assert not caplog.records
