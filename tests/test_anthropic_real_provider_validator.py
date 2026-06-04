"""Tests for Anthropic real provider validator — no internet required, uses mocks."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_LIB = PROJECT_ROOT / "scripts" / "lib"
if str(SCRIPT_LIB) not in sys.path:
    sys.path.insert(0, str(SCRIPT_LIB))

from anthropic_real_validator import (
    AnthropicRealValidator,
    estimate_anthropic_cost_usd,
    get_fx_rate_brl,
    load_env_local,
    mask_key,
    sanitize_log,
)

ANTHROPIC_MASK_KEY = "sk-" "ant-test-key-1234567890abcdef"
ANTHROPIC_TEST_KEY = "test-anthropic-key"
ANTHROPIC_SANITIZE_KEY = "sk-" "ant-test-key-1234567890"


def test_estimate_anthropic_cost_usd():
    cost = estimate_anthropic_cost_usd("claude-3-haiku-20240307", 1000, 500)
    expected = (1000 / 1_000_000 * 0.25) + (500 / 1_000_000 * 1.25)
    assert cost == expected


def test_estimate_anthropic_cost_sonnet():
    cost = estimate_anthropic_cost_usd("claude-3-5-sonnet-20241022", 1000, 500)
    expected = (1000 / 1_000_000 * 3.00) + (500 / 1_000_000 * 15.00)
    assert cost == expected


def test_estimate_anthropic_cost_unknown_model():
    cost = estimate_anthropic_cost_usd("unknown-model", 1000, 500)
    assert cost == 0.0


def test_estimate_anthropic_cost_fuzzy_match():
    cost = estimate_anthropic_cost_usd("ft:claude-3-haiku:org::abc123", 100, 50)
    assert cost > 0
    assert isinstance(cost, float)


def test_get_fx_rate_brl_default():
    rate = get_fx_rate_brl()
    assert rate == 5.00


def test_get_fx_rate_brl_from_env(monkeypatch):
    monkeypatch.setenv("USD_BRL_RATE", "5.50")
    rate = get_fx_rate_brl()
    assert rate == 5.50


def test_mask_key():
    assert mask_key(ANTHROPIC_MASK_KEY) == "sk-a****cdef"
    assert mask_key("abc") == "********"
    assert mask_key("") == "********"


def test_sanitize_log_truncates():
    long = {"data": "x" * 1000}
    result = sanitize_log(long, max_chars=50)
    assert len(result) <= 50 + 20


def test_load_env_local_returns_dict(tmp_path):
    env_file = tmp_path / ".env.local"
    env_file.write_text("ANTHROPIC_API_KEY=test-anthropic-key\nANTHROPIC_PROVIDER_ENABLED=true\n")
    result = load_env_local()
    assert isinstance(result, dict)


class MockArgs:
    def __init__(self, dry_run=True, real=False, max_cost_brl=2.0, model="claude-3-haiku-20240307", output_dir="/tmp"):
        self.dry_run = dry_run
        self.real = real
        self.max_cost_brl = max_cost_brl
        self.model = model
        self.output_dir = output_dir


def test_validator_skips_when_no_key():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true"}
    args = MockArgs(dry_run=False, real=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    assert report["status"] == "ANTHROPIC_REAL_SKIP"


def test_validator_skips_when_rpv_disabled():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "false", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=False, real=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    assert report["status"] == "ANTHROPIC_REAL_SKIP"


def test_validator_skips_when_ape_disabled():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "false", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=False, real=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    assert report["status"] == "ANTHROPIC_REAL_SKIP"


def test_validator_dry_run_passes():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    assert report["status"] == "ANTHROPIC_REAL_PASS"
    assert report["dry_run"] is True


def test_validator_dry_run_no_real_calls():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    check_names = [c["check"] for c in report["checks"]]
    assert "health" not in check_names
    assert "messages" not in check_names


def test_validator_report_has_expected_fields():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=True)
    v = AnthropicRealValidator(args, env)
    report = v.run()
    assert "validator" in report
    assert "timestamp" in report
    assert "status" in report
    assert "model" in report
    assert "checks" in report
    assert "summary" in report


def test_validator_writes_report(tmp_path):
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=True, output_dir=str(tmp_path))
    v = AnthropicRealValidator(args, env)
    v.run()
    rp, mp = v.write_report()
    assert rp.exists()
    assert mp.exists()
    with open(rp) as f:
        data = json.load(f)
    assert data["status"] == "ANTHROPIC_REAL_PASS"


def test_validator_masks_key_in_report(tmp_path):
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_SANITIZE_KEY}
    args = MockArgs(dry_run=True, output_dir=str(tmp_path))
    v = AnthropicRealValidator(args, env)
    report = v.run()
    sanitized = json.dumps(report)
    assert ANTHROPIC_SANITIZE_KEY not in sanitized
    assert "sk-a" in sanitized or "****" in sanitized


def test_validator_respects_max_cost_brl():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=True, max_cost_brl=5.0)
    v = AnthropicRealValidator(args, env)
    assert v.max_cost_brl == 5.0


def test_skip_responses_unsupported():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=False, real=True)
    v = AnthropicRealValidator(args, env)
    v._check_responses()
    responses_checks = [c for c in v.report["checks"] if c["check"] == "responses"]
    assert any("SKIP_UNSUPPORTED_CAPABILITY" in c["detail"] for c in responses_checks)


def test_skip_embeddings_unsupported():
    env = {"REAL_PROVIDER_VALIDATION_ENABLED": "true", "ANTHROPIC_PROVIDER_ENABLED": "true", "ANTHROPIC_API_KEY": ANTHROPIC_TEST_KEY}
    args = MockArgs(dry_run=False, real=True)
    v = AnthropicRealValidator(args, env)
    v._check_embeddings()
    emb_checks = [c for c in v.report["checks"] if c["check"] == "embeddings"]
    assert any("SKIP_UNSUPPORTED_CAPABILITY" in c["detail"] for c in emb_checks)


def test_sanitize_log_truncates_long_values():
    long_val = "sk-ant-" + "a" * 500
    report_data = {"key": long_val}
    sanitized = sanitize_log(report_data, max_chars=50)
    assert len(sanitized) <= 80
