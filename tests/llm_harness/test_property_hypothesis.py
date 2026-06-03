from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.sanitizer import Sanitizer
from scripts.llm_harness.schemas import AgentActionResponse

# Set hypothesis profile settings to keep CI execution fast
settings.register_profile("ci", max_examples=20)
settings.load_profile("ci")

# Strategy for dictionary values
value_strategy = st.none() | st.booleans() | st.integers() | st.floats() | st.text()

@given(st.text())
def test_sanitizer_redacts_simulated_secrets(text):
    """Sanitizer must always redact known secret formats inserted in random text."""
    aws_key = "AKIA1234567890ABCDEF"
    tainted = f"{text} {aws_key}"
    sanitized = Sanitizer.sanitize_text(tainted)
    assert aws_key not in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized

@given(st.lists(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"), min_size=1, max_size=3))
def test_policy_engine_blocks_path_traversal(parts):
    """PolicyEngine must block any file path trying to traversal outside workspace."""
    engine = PolicyEngine()
    path_suffix = "/".join(parts)
    traversal_path = f"../{path_suffix}"
    
    decision = engine.evaluate_file_path(traversal_path)
    assert not decision.allowed
    assert "traversal" in decision.reason.lower() or "absolute" in decision.reason.lower()

@given(st.dictionaries(st.text(), value_strategy))
def test_config_loader_safety(d):
    """Config loader must handle arbitrary configuration dicts without crashing."""
    try:
        # Extra arguments should be ignored or raise ValidationError, not crash
        HarnessConfig(**d)
    except (ValidationError, TypeError, ValueError):
        pass

@given(st.dictionaries(st.text(), value_strategy))
def test_schema_validation_rejects_malformed_actions(d):
    """Action validation must safely reject arbitrary/malformed payloads."""
    try:
        AgentActionResponse.model_validate(d)
    except ValidationError:
        pass
    except Exception:
        # ValidationError is expected, any other exception is a bug
        assert False, "Unexpected non-ValidationError crash"
