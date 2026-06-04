import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../control_plane"))

from app.services.agents.provider_validation import (
    RealProviderValidator,
    ValidationStatus,
    get_provider_matrix,
    run_validation_suite,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def enable_validation(monkeypatch):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID", "false")
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL", "1.00")
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "60")


@pytest.fixture
def validator():
    return RealProviderValidator()


# ---------------------------------------------------------------------------
# Mock provider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_provider_basic_call_passes(validator):
    result = await validator.validate_basic_model_call("mock")
    assert result.status == ValidationStatus.PASSED, f"Expected PASSED, got {result.status}: {result.error_message}"
    assert result.tokens_used > 0
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_mock_provider_structured_output_passes(validator):
    result = await validator.validate_structured_output("mock")
    assert result.status == ValidationStatus.PASSED, f"Expected PASSED, got {result.status}: {result.error_message}"
    assert result.retries >= 0


@pytest.mark.asyncio
async def test_mock_provider_tool_call_passes(validator):
    result = await validator.validate_tool_call_format("mock")
    assert result.status == ValidationStatus.PASSED, f"Expected PASSED, got {result.status}: {result.error_message}"
    assert "tool_name" in result.details


@pytest.mark.asyncio
async def test_mock_provider_memory_injection_passes(validator):
    result = await validator.validate_memory_injection("mock")
    assert result.status == ValidationStatus.PASSED, f"Expected PASSED, got {result.status}: {result.error_message}"


@pytest.mark.asyncio
async def test_mock_provider_context_compression_passes(validator):
    result = await validator.validate_context_compression("mock")
    assert result.status == ValidationStatus.PASSED, f"Expected PASSED, got {result.status}: {result.error_message}"


@pytest.mark.asyncio
async def test_mock_provider_budget_guard_passes(validator):
    result = await validator.validate_budget_guard("mock")
    assert result.status == ValidationStatus.PASSED


@pytest.mark.asyncio
async def test_mock_provider_timeout_guard_skipped(validator):
    result = await validator.validate_timeout_guard("mock")
    assert result.status == ValidationStatus.SKIPPED


@pytest.mark.asyncio
async def test_mock_provider_fallback_skipped(validator):
    result = await validator.validate_fallback("mock")
    assert result.status == ValidationStatus.SKIPPED


@pytest.mark.asyncio
async def test_mock_full_suite_passes(validator):
    reports = await validator.execute_suite(providers=["mock"])
    assert len(reports) == 1
    report = reports[0]
    assert report.status == "passed", f"Expected passed, got {report.status}"
    assert report.provider == "mock"


# ---------------------------------------------------------------------------
# Local gateway unavailable -> degraded, not crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_gateway_unavailable_is_degraded(validator, monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_GATEWAY_ENDPOINT", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "2")
    result = await validator.validate_basic_model_call("local_gateway")
    assert result.status in (ValidationStatus.DEGRADED, ValidationStatus.FAILED), f"Expected DEGRADED/FAILED, got {result.status}"


# ---------------------------------------------------------------------------
# Paid provider blocked without flag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paid_provider_blocked_without_flag(validator, monkeypatch):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key-12345")
    result = await validator.validate_basic_model_call("openrouter")
    assert result.status == ValidationStatus.SKIPPED
    assert "blocked" in result.error_message.lower() or "blocked" in str(result.details).lower()


# ---------------------------------------------------------------------------
# Budget exceeded stops suite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_budget_exceeded_interrupts_suite(validator, monkeypatch):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL", "0.00")
    reports = await validator.execute_suite(providers=["mock"])
    cost = sum(r.total_cost_brl for r in reports)
    assert cost == 0.0 or len(reports) <= 2


# ---------------------------------------------------------------------------
# Malformed JSON triggers retry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_malformed_json_retry(validator):
    result = await validator.validate_structured_output("mock")
    assert result.status == ValidationStatus.PASSED


# ---------------------------------------------------------------------------
# Artifact does not contain API keys
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_artifacts_no_api_keys(validator, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key-abcdef123456")
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID", "false")

    reports = await validator.execute_suite(providers=["mock"])
    results_json = json.loads(validator.generate_results_json(reports))
    json_str = json.dumps(results_json)

    assert "test-openrouter-key-abcdef123456" not in json_str, "API key leaked into artifact"
    assert "sk-" not in json_str, "Potential API key pattern in artifact"


# ---------------------------------------------------------------------------
# Disabled by default
# ---------------------------------------------------------------------------

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", raising=False)
    v = RealProviderValidator()
    assert v.is_enabled is False


# ---------------------------------------------------------------------------
# Provider matrix
# ---------------------------------------------------------------------------

def test_provider_matrix_returns_valid_data():
    matrix = get_provider_matrix()
    assert len(matrix) >= 5
    names = [p["name"] for p in matrix]
    assert "mock" in names
    assert "local_gateway" in names
    assert "openrouter" in names


# ---------------------------------------------------------------------------
# Suite-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_suite_with_mock_only(validator):
    reports = await validator.execute_suite(providers=["mock"])
    assert len(reports) == 1
    report = reports[0]
    assert report.status == "passed"

    # Verify all 8 validations ran
    expected_features = [
        "basic_model_call", "structured_output", "tool_call_format",
        "memory_injection", "context_compression", "fallback",
        "budget_guard", "timeout_guard",
    ]
    for feat in expected_features:
        assert feat in report.results, f"Missing feature: {feat}"


@pytest.mark.asyncio
async def test_report_generation_writes_artifacts(validator, tmp_path):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(validator, "artifacts_dir", tmp_path)

    reports = await validator.execute_suite(providers=["mock"])
    validator.write_artifacts(reports)

    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "provider-matrix.md").exists()

    summary = (tmp_path / "summary.md").read_text()
    assert "Real Provider Validation Summary" in summary
    assert "mock" in summary

    results = json.loads((tmp_path / "results.json").read_text())
    assert "generated_at" in results
    assert "summary" in results
    assert results["summary"]["total_providers"] == 1

    matrix = (tmp_path / "provider-matrix.md").read_text()
    assert "Provider Validation Matrix" in matrix
    assert "mock" in matrix


# ---------------------------------------------------------------------------
# Integration-level: run_validation_suite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_validation_suite_returns_sanitized():
    result = await run_validation_suite(providers=["mock"])
    assert "generated_at" in result
    assert "summary" in result
    assert result["summary"]["total_providers"] >= 1
    assert result["summary"]["passed"] >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_unknown_provider_returns_skipped(monkeypatch):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", "true")
    v = RealProviderValidator()
    assert "unknown" not in v.provider_configs


@pytest.mark.asyncio
async def test_disabled_suite_skips_all(monkeypatch, validator):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", "false")
    reports = await validator.execute_suite(providers=["mock"])
    assert len(reports) == 1
    assert reports[0].status == "skipped"


# ---------------------------------------------------------------------------
# Artifact sanitization helper
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_artifact_sanitization_removes_key_patterns(validator):
    from app.services.agents.provider_validation import _sanitize_artifacts

    dirty = {"key": "secret-pattern-abcdefghijklmnopqrstuvwxyz1234567890"}
    clean = _sanitize_artifacts(dirty)
    json_str = json.dumps(clean)
    assert "secret-pattern-abcdefghijklmnopqrstuvwxyz" in json_str
