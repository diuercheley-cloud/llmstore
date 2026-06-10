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


def test_pricing_manager_with_reasoning_tokens():
    pm = PricingManager()
    #
    # 1M prompt tokens, 1M completion tokens, 900k reasoning_tokens
    # For gpt-4o: $5/1M prompt, $15/1M completion
    # With reasoning: prompt_cost = (1M + 900k) / 1M * 5 = 1.9 * 5 = 9.5
    #                 completion_cost = (100k) / 1M * 15 = 0.1 * 15 = 1.5
    #                 total = 11.0
    result = pm.calculate_cost("gpt-4o", 1_000_000, 1_000_000, reasoning_tokens=900_000)
    assert result is not None
    assert result.cost == 11.0
    assert result.known is True


def test_pricing_manager_reasoning_tokens_greater_than_completion():
    pm = PricingManager()
    result = pm.calculate_cost("gpt-4o", 1_000_000, 100_000, reasoning_tokens=200_000)
    assert result is not None
    # completion - reasoning = negative, clamped to 0
    assert result.cost == 6.0  # (1M + 200k) / 1M * 5 + 0 = 6.0


def test_pricing_manager_model_override_with_reasoning():
    pm = PricingManager()
    pm.set_model_override("gpt-4o")
    result = pm.calculate_cost("unknown-model", 1_000_000, 1_000_000, reasoning_tokens=500_000)
    assert result is not None
    assert result.cost == 15.0
    assert result.known is True
