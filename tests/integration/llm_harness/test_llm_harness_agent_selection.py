import pytest

from scripts.llm_harness.agent_client import AgentClient


@pytest.mark.asyncio
async def test_agent_selection_logic():
    client = AgentClient(agent_id="test-agent")
    config = await client.get_agent_config()
    # Simple selection logic check: if agent exists, it's selected
    assert config["id"] == "test-agent"
    assert config["type"] == "coding"
