import json
import os

import pytest

from scripts.llm_harness.providers import (
    _PROVIDER_REGISTRY,
    StubProvider,
    create_code_agent,
)


def test_provider_registration():
    """
    Ensure all expected providers are registered in the registry.
    """
    expected = {
        "stub",
        "openai-compatible",
        "local-openai-compatible",
        "anthropic",
        "google",
        "control-plane",
    }
    assert expected.issubset(_PROVIDER_REGISTRY.keys())


def test_stub_provider_config():
    """
    Validate StubProvider configuration and repr.
    """
    config = {"agent_id": "test-stub"}
    agent = create_code_agent("stub", config)
    assert isinstance(agent, StubProvider)
    assert agent.agent_id == "test-stub"
    # repr check
    repr_str = repr(agent)
    assert "StubProvider" in repr_str
    assert "test-stub" in repr_str


def test_openai_compatible_provider_validation():
    """
    Validate OpenAICompatibleProvider error cases on missing fields.
    """
    # 1. Missing base_url
    config = {"model": "gpt-4"}
    agent = create_code_agent("openai-compatible", config)
    with pytest.raises(ValueError, match="base_url is required"):
        agent._validate_config()

    # 2. Missing model
    config = {"base_url": "http://localhost:8000"}
    agent = create_code_agent("openai-compatible", config)
    with pytest.raises(ValueError, match="model is required"):
        agent._validate_config()

    # 3. Missing API key
    config = {
        "base_url": "http://localhost:8000",
        "model": "gpt-4",
        "api_key_env": "NON_EXISTENT_KEY_VAR",
    }
    agent = create_code_agent("openai-compatible", config)
    with pytest.raises(ValueError, match="API key not found in environment variable"):
        agent._validate_config()


def test_local_openai_compatible_provider_validation():
    """
    Validate LocalOpenAICompatibleProvider configuration validation (which bypasses API key check
    and allows model auto-selection).
    """
    # 1. Missing base_url
    config = {"model": "llama3"}
    agent = create_code_agent("local-openai-compatible", config)
    with pytest.raises(ValueError, match="base_url is required"):
        agent._validate_config()

    # 2. Success when base_url is provided without an explicit model (no API key needed)
    config = {"base_url": "http://localhost:11434"}
    agent = create_code_agent("local-openai-compatible", config)
    agent._validate_config()

    # 3. Success when base_url and model are provided (no API key needed)
    config = {"base_url": "http://localhost:11434", "model": "llama3"}
    agent = create_code_agent("local-openai-compatible", config)
    # This should not raise an error
    agent._validate_config()


def test_anthropic_provider_validation():
    """
    Validate AnthropicProvider key validation.
    """
    config = {"api_key_env": "NON_EXISTENT_KEY_VAR"}
    agent = create_code_agent("anthropic", config)
    with pytest.raises(ValueError, match="API key not found in environment variable"):
        agent._validate_config()


def test_google_provider_validation():
    """
    Validate GoogleProvider key validation.
    """
    config = {"api_key_env": "NON_EXISTENT_KEY_VAR"}
    agent = create_code_agent("google", config)
    with pytest.raises(ValueError, match="API key not found in environment variable"):
        agent._validate_config()


def test_control_plane_provider_validation():
    """
    Validate ControlPlaneProvider validation.
    """
    # Missing base_url
    config = {"agent_id": "test-agent"}
    agent = create_code_agent("control-plane", config)
    with pytest.raises(ValueError, match="base_url is required for provider control-plane"):
        agent._validate_config()


def test_provider_repr_safety():
    """
    Verify that the __repr__ of all providers is safe and does not leak API keys.
    """
    os.environ["TEST_API_KEY_ENV"] = "MOCK_API_KEY_VALUE"
    try:
        config = {
            "agent_id": "test-repr-agent",
            "base_url": "https://api.test.com",
            "model": "gpt-test",
            "api_key_env": "TEST_API_KEY_ENV",
        }
        for name in _PROVIDER_REGISTRY.keys():
            agent = create_code_agent(name, config)
            repr_str = repr(agent)
            # Ensure the class name is present
            assert agent.__class__.__name__ in repr_str
            # Ensure the env var name is present
            assert "TEST_API_KEY_ENV" in repr_str
            # Ensure the actual secret is NEVER in repr
            assert "MOCK_API_KEY_VALUE" not in repr_str
    finally:
        if "TEST_API_KEY_ENV" in os.environ:
            del os.environ["TEST_API_KEY_ENV"]


@pytest.mark.parametrize(
    "valid_json",
    [
        '{"type": "plan", "reason": "plan something", "payload": {"message": "hello"}}',
        '{"type": "read_file", "reason": "read file contents", "payload": {"path": "main.py"}}',
        '{"type": "apply_patch", "reason": "applying diff", "payload": {"diff": "some-diff"}}',
        '{"type": "run_tests", "reason": "testing patch", "payload": {"test_path": "tests/"}}',
        '{"type": "final", "reason": "fixed task", "payload": {"message": "done"}}',
        # Markdown wrapped
        '```json\n{"type": "final", "reason": "done", "payload": {"message": "ok"}}\n```',
    ],
)
def test_provider_json_action_parsing_valid(valid_json: str):
    """
    Verify that valid action payloads are successfully parsed and transformed.
    """
    agent = create_code_agent("stub", {})
    transformed_str = agent._validate_and_transform_action(valid_json)
    transformed = json.loads(transformed_str)

    # Assert normalized fields exist
    assert "action_type" in transformed
    assert transformed["action_type"] in {"plan", "read_file", "apply_patch", "run_tests", "final"}
    if "reason" in valid_json:
        assert "reason" in transformed


@pytest.mark.parametrize(
    "invalid_json, error_match",
    [
        ("{invalid json", "invalid_json"),
        ('{"reason": "missing type"}', "schema_validation_failed"),
        ('{"type": "invalid_type", "payload": {}}', "unsupported_action"),
        ('{"type": "plan", "payload": "not_a_dict"}', "schema_validation_failed"),
        ("[]", "invalid_payload"),
    ],
)
def test_provider_json_action_parsing_invalid(invalid_json: str, error_match: str):
    """
    Verify that invalid action payloads are properly rejected with clear errors.
    """
    agent = create_code_agent("stub", {})
    with pytest.raises(ValueError, match=error_match):
        agent._validate_and_transform_action(invalid_json)
