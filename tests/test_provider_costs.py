
from app.services.billing.pricing_engine import estimate_provider_cost, get_provider_pricing_config


def test_get_provider_pricing_config():
    cfg = get_provider_pricing_config()
    assert "providers" in cfg
    assert "fx_rate_brl_per_usd" in cfg


def test_all_providers_have_pricing():
    cfg = get_provider_pricing_config()
    providers = cfg.get("providers", {})
    for pid, pcfg in providers.items():
        assert "cost_usd_per_1k_prompt" in pcfg
        assert "cost_usd_per_1k_completion" in pcfg
        assert "pricing_configured" in pcfg


def test_local_cost_is_zero():
    result = estimate_provider_cost("local", 1000, 500)
    assert result.cost_usd == 0.0
    assert result.cost_brl == 0.0


def test_mock_cost_is_zero():
    result = estimate_provider_cost("mock", 1000, 500)
    assert result.cost_usd == 0.0
    assert result.pricing_configured is True


def test_lmstudio_cost_is_zero():
    result = estimate_provider_cost("lmstudio", 1000, 500)
    assert result.cost_usd == 0.0


def test_openai_not_configured_by_default():
    result = estimate_provider_cost("openai", 1000, 500)
    assert result.pricing_configured is False


def test_anthropic_not_configured_by_default():
    result = estimate_provider_cost("anthropic", 1000, 500)
    assert result.pricing_configured is False


def test_deepseek_not_configured_by_default():
    result = estimate_provider_cost("deepseek", 1000, 500)
    assert result.pricing_configured is False


def test_zero_tokens():
    result = estimate_provider_cost("local", 0, 0)
    assert result.cost_usd == 0.0
    assert result.cost_brl == 0.0


def test_large_tokens():
    result = estimate_provider_cost("local", 100000, 50000)
    assert result.cost_usd == 0.0


def test_no_secrets_in_config():
    cfg = get_provider_pricing_config()
    dump = str(cfg)
    assert "api_key" not in dump.lower()
    assert "secret" not in dump.lower()
    assert "sk-" not in dump
