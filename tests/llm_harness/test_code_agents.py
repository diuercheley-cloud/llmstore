
import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.providers import StubProvider


def test_stub_provider_allowed():
    # AgentClient should allow 'stub' provider
    client = AgentClient(agent_id="test-stub", provider="stub")
    assert isinstance(client._provider_inst, StubProvider)
    assert client.provider == "stub"

def test_openai_compatible_requires_config():
    # OpenAICompatibleProvider should fail if base_url or model is missing during validation
    client = AgentClient(
        agent_id="test-openai",
        provider="openai-compatible",
        base_url="",
        model=""
    )
    with pytest.raises(ValueError, match="base_url is required"):
        # Validation happens during chat_completion or health_check
        import asyncio
        asyncio.run(client.health_check())

def test_unknown_provider_fails():
    with pytest.raises(ValueError, match="Unknown provider: nonexistent"):
        AgentClient(agent_id="test", provider="nonexistent")

def test_agent_repr_is_safe():
    client = AgentClient(
        agent_id="secret-agent",
        provider="stub",
        model="gpt-4",
        base_url="http://localhost:8080"
    )
    r = repr(client)
    assert "StubProvider" in r
    assert "secret-agent" in r
    assert "gpt-4" in r
    # Repr should not contain sensitive info if any were passed (though here we don't pass keys in config directly)
    assert "api_key" not in r.lower() or "env" in r.lower()
