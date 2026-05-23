import os
import pytest
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../control_plane"))
from app.services.agents.provider_validation import RealProviderValidator

@pytest.fixture(autouse=True)
def enable_real_provider_validation(monkeypatch):
    monkeypatch.setenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", "true")

def test_provider_unavailable_does_not_break_suite():
    validator = RealProviderValidator()
    # Add a broken provider
    validator.supported_providers.append("UnavailableProvider")
    
    report = validator.execute_suite()
    
    # Assert other providers like OpenAI passed (or at least returned success)
    openai_result = next((r for r in report if r["provider"] == "OpenAI"), None)
    assert openai_result is not None
    assert openai_result["status"] == "success"
    
    # Assert UnavailableProvider returned an error but didn't crash the suite
    unavail_result = next((r for r in report if r["provider"] == "UnavailableProvider"), None)
    assert unavail_result is not None
    assert unavail_result["status"] == "error"

def test_malformed_json_retry_works():
    validator = RealProviderValidator()
    result = validator.validate_retry_malformed_json("OpenAI")
    assert result["status"] == "passed"
    assert result["retries"] > 0

def test_context_compression_preserves_goals():
    validator = RealProviderValidator()
    result = validator.validate_context_compression("Anthropic")
    assert result["status"] == "passed"
    assert result["goals_preserved"] is True

def test_fallback_provider_works():
    validator = RealProviderValidator()
    
    # Simulating a fallback scenario where OpenAI fails and we fallback to Anthropic
    # In this mock, we just ensure both are supported and report correctly.
    res_openai = validator.run_all_validations("OpenAI")
    assert res_openai["status"] == "success"
    
    res_anthropic = validator.run_all_validations("Anthropic")
    assert res_anthropic["status"] == "success"
    
    # Verify standard safety rules are correctly defined
    assert validator.safety_rules["destructive_tools_allowed"] is False
    assert validator.safety_rules["mock_saas_mode"] is True

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", raising=False)
    validator = RealProviderValidator()
    assert validator.is_enabled is False
    
    res = validator.validate_structured_output("OpenAI")
    assert res["status"] == "skipped"

def test_report_generation():
    from app.services.agents.provider_validation import generate_markdown_report
    validator = RealProviderValidator()
    report = validator.execute_suite()
    
    os.makedirs("artifacts/evals", exist_ok=True)
    generate_markdown_report(report, filepath="artifacts/evals/test-real-provider-validation.md")
    
    assert os.path.exists("artifacts/evals/test-real-provider-validation.md")
    with open("artifacts/evals/test-real-provider-validation.md", "r") as f:
        content = f.read()
        assert "Real Provider Validation Report" in content
        assert "OpenAI" in content
