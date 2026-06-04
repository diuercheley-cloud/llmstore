import os
import yaml
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from scripts.llm_harness.mas.registry import AgentRegistry
from scripts.llm_harness.mas.team_orchestrator import TeamOrchestrator
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.workspace import Workspace

@pytest.fixture
def mock_registry_yaml(tmp_path):
    registry_data = {
        "agents": {
            "architect": {
                "role": "Architect",
                "prompt": "You are the architect.",
                "tools": ["read_file", "list_dir"]
            },
            "developer": {
                "role": "Developer",
                "prompt": "You are the developer.",
                "tools": ["write_file", "read_file"]
            },
            "tester": {
                "role": "Tester",
                "prompt": "You are the tester.",
                "tools": ["run_tests"]
            },
            "hacker": {
                "role": "Hacker",
                "prompt": "Try to break things.",
                "tools": ["delete_all"] # Destructive
            }
        },
        "teams": {
            "dev_team": {
                "name": "Dev Team",
                "description": "A standard dev team.",
                "topology": "linear",
                "members": [
                    {"agent_id": "architect", "role": "planner"},
                    {"agent_id": "developer", "role": "coder"},
                    {"agent_id": "tester", "role": "qa"}
                ]
            }
        },
        "destructive_tools": ["delete_all"]
    }
    registry_file = tmp_path / "agent-registry.yaml"
    with open(registry_file, "w") as f:
        yaml.dump(registry_data, f)
    return str(registry_file)

def create_loop(config, tmp_path):
    client = AgentClient(agent_id="test-agent", provider="stub", model="test")
    ws = Workspace(base_path=str(tmp_path / "ws"))
    ws.path = str(tmp_path / "ws")
    os.makedirs(ws.path, exist_ok=True)
    loop = CodingLoop(agent_client=client, workspace=ws)
    loop.config = config
    return loop

@pytest.mark.asyncio
async def test_linear_team_execution(mock_registry_yaml, tmp_path):
    config = HarnessConfig(agent_registry_file=mock_registry_yaml)
    loop = create_loop(config, tmp_path)
    
    # Mock loop.run to return success results
    loop.run = AsyncMock(side_effect=[
        ExecutionResult(success=True, message="Architect finished"),
        ExecutionResult(success=True, message="Developer finished"),
        ExecutionResult(success=True, message="Tester finished")
    ])
    
    orchestrator = TeamOrchestrator(loop)
    result = await orchestrator.run_team("dev_team", "Implement feature X")
    
    assert result.success is True
    assert "Tester finished" in result.message
    assert loop.run.call_count == 3

@pytest.mark.asyncio
async def test_role_based_tool_blocking(mock_registry_yaml, tmp_path):
    config = HarnessConfig(agent_registry_file=mock_registry_yaml)
    loop = create_loop(config, tmp_path)
    
    orchestrator = TeamOrchestrator(loop)
    
    # Simulate architect trying to call write_file (not in its tools)
    loop.current_agent = "architect"
    loop.current_team = "dev_team"
    from scripts.llm_harness.mas.blackboard import Blackboard
    loop.blackboard = Blackboard("test")
    
    with pytest.raises(PermissionError, match="not allowed for agent 'architect'"):
        await loop._execute_single_action({"type": "write_file", "path": "test.txt", "content": "hello"})
    
    assert any(e["type"] == "policy_blocked" for e in loop.blackboard.audit_log)

@pytest.mark.asyncio
async def test_destructive_tool_hard_deny(mock_registry_yaml, tmp_path):
    config = HarnessConfig(agent_registry_file=mock_registry_yaml)
    loop = create_loop(config, tmp_path)
    orchestrator = TeamOrchestrator(loop)
    
    loop.current_agent = "hacker"
    loop.current_team = None
    loop.blackboard = None
    
    with pytest.raises(PermissionError, match="Hard-deny"):
        await loop._execute_single_action({"type": "delete_all"})
