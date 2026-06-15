from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from scripts.llm_harness.mas.blackboard import Blackboard
from scripts.llm_harness.mas.contracts import AgentDefinition, AgentTeam, TeamMember
from scripts.llm_harness.mas.orchestrator import Orchestrator
from scripts.llm_harness.mas.teams import TeamManager
from scripts.llm_harness.models import ExecutionResult


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.get_agent.side_effect = lambda aid: AgentDefinition(
        role=aid, prompt=f"Prompt for {aid}", tools=["read", "write"]
    )
    return registry


def test_validate_team_yaml(mock_registry, tmp_path):
    team_data = {
        "team_name": "DevTeam",
        "description": "A team of devs",
        "members": [
            {"agent_id": "planner", "role": "planner"},
            {"agent_id": "coder", "role": "coder"},
            {"agent_id": "reviewer", "role": "reviewer"},
        ],
        "topology": "planner_coder_reviewer",
    }

    team_file = tmp_path / "team.yaml"
    with open(team_file, "w") as f:
        yaml.dump(team_data, f)

    manager = TeamManager(mock_registry)
    team = manager.load_team_from_yaml(str(team_file))

    assert team.team_name == "DevTeam"
    assert team.topology == "planner_coder_reviewer"


def test_blackboard_redaction_and_hashing():
    bb = Blackboard("Test Task")
    bb.add_message("agent1", "agent2", "My secret key is sk-example1234567890abcdef1234567890")

    msg = bb.state.messages[0]
    assert "[REDACTED_API_KEY]" in msg.content
    assert "sk-" not in msg.content
    assert msg.hash is not None
    assert len(msg.hash) == 64  # SHA-256


@pytest.mark.asyncio
async def test_orchestrator_debate_stop_condition(mock_registry):
    coding_loop = MagicMock()
    coding_loop.run = AsyncMock(
        return_value=ExecutionResult(success=True, message="I agree, let's stop.")
    )
    coding_loop.config = MagicMock()
    coding_loop.config.agent_registry_file = "fake.yaml"

    team = AgentTeam(
        team_name="DebateTeam",
        description="Debating team",
        members=[
            TeamMember(agent_id="agent1", role="debater"),
            TeamMember(agent_id="agent2", role="debater"),
        ],
        topology="debate",
        stop_conditions=["let's stop"],
    )

    # Mock Registry.load
    with MagicMock() as mock_load:
        from scripts.llm_harness.mas.registry import AgentRegistry

        original_load = AgentRegistry.load
        AgentRegistry.load = MagicMock(return_value=mock_registry)

        orchestrator = Orchestrator(coding_loop)
        result = await orchestrator.run(team, "Should we stop?")

        assert result.success is True
        assert "let's stop" in result.message.lower()

        AgentRegistry.load = original_load


@pytest.mark.asyncio
async def test_orchestrator_pcr_flow(mock_registry):
    coding_loop = MagicMock()

    # Mock different responses for different roles
    async def side_effect(prompt, **kwargs):
        if "detailed plan" in prompt:
            return ExecutionResult(success=True, message="Here is the plan.")
        if "Implement" in prompt:
            return ExecutionResult(success=True, message="Here is the code.")
        if "Review" in prompt:
            return ExecutionResult(success=True, message="LGTM")
        return ExecutionResult(success=False, message="Unknown prompt")

    coding_loop.run = AsyncMock(side_effect=side_effect)
    coding_loop.config = MagicMock()

    team = AgentTeam(
        team_name="PCRTeam",
        description="PCR team",
        members=[
            TeamMember(agent_id="planner", role="planner"),
            TeamMember(agent_id="coder", role="coder"),
            TeamMember(agent_id="reviewer", role="reviewer"),
        ],
        topology="planner_coder_reviewer",
    )

    with MagicMock() as mock_load:
        from scripts.llm_harness.mas.registry import AgentRegistry

        original_load = AgentRegistry.load
        AgentRegistry.load = MagicMock(return_value=mock_registry)

        orchestrator = Orchestrator(coding_loop)
        result = await orchestrator.run(team, "Build a hello world")

        assert result.success is True
        assert "Here is the code" in result.message

        AgentRegistry.load = original_load
