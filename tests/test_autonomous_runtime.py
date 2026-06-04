import os
import yaml
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from scripts.llm_harness.mas.registry import AgentRegistry
from scripts.llm_harness.mas.autonomous_runtime import AutonomousAgentRuntime
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.config import HarnessConfig
from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.workspace import Workspace

@pytest.fixture
def mock_registry_yaml(tmp_path):
    registry_data = {
        "agents": {
            "maintainer": {
                "role": "Maintainer",
                "prompt": "You are the maintainer.",
                "tools": ["read_file", "run_tests"]
            }
        },
        "teams": {},
        "destructive_tools": []
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
async def test_autonomous_cycle_success(mock_registry_yaml, tmp_path):
    config = HarnessConfig(agent_registry_file=mock_registry_yaml, checkpoint_dir=str(tmp_path / "cp"))
    loop = create_loop(config, tmp_path)
    
    runtime = AutonomousAgentRuntime(loop)
    
    # Mock _decide to return one action then final
    runtime._decide = AsyncMock(side_effect=[
        {"type": "action", "next_agent": "maintainer", "instruction": "Check tests"},
        {"type": "final", "message": "All good"}
    ])
    
    loop.run = AsyncMock(return_value=ExecutionResult(success=True, message="Tests passed"))
    
    result = await runtime.run_autonomous(agent_id="maintainer", goal="Maintain codebase", max_steps=5, cooldown=0)
    
    assert result.success is True
    assert "All good" in result.message
    assert runtime._decide.call_count == 2
    assert loop.run.call_count == 1

@pytest.mark.asyncio
async def test_autonomous_budget_exceeded(mock_registry_yaml, tmp_path):
    config = HarnessConfig(agent_registry_file=mock_registry_yaml, checkpoint_dir=str(tmp_path / "cp"))
    loop = create_loop(config, tmp_path)
    runtime = AutonomousAgentRuntime(loop)
    
    runtime._decide = AsyncMock(return_value={"type": "action", "next_agent": "maintainer", "instruction": "Work"})
    
    # Mock loop.run to return result with cost
    loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, 
        message="Done",
        metrics={"estimated_cost": 1.0}
    ))
    
    result = await runtime.run_autonomous(agent_id="maintainer", goal="Expensive task", budget=0.5, max_steps=5, cooldown=0)
    
    assert result.success is False
    assert "Budget exceeded" in result.message

@pytest.mark.asyncio
async def test_autonomous_pause_resume(mock_registry_yaml, tmp_path):
    config = HarnessConfig(
        agent_registry_file=mock_registry_yaml, 
        checkpoint_dir=str(tmp_path / "cp"),
        checkpoint_every_step=True
    )
    loop = create_loop(config, tmp_path)
    runtime = AutonomousAgentRuntime(loop)
    
    # Mock _decide to allow pause
    runtime._decide = AsyncMock(return_value={"type": "action", "next_agent": "maintainer", "instruction": "Step"})
    loop.run = AsyncMock(return_value=ExecutionResult(success=True, message="Step done"))
    
    # We'll use a task that we manually pause
    run_id = "test-pause-run"
    
    # Start in background or mock the loop condition
    # Instead of true async concurrency which is hard to control in tests, 
    # we'll mock the check for 'paused' status
    
    # Simulate a run that pauses after 1 step
    original_side_effect = runtime._decide.side_effect
    def side_effect_with_pause(*args, **kwargs):
        # We need to find the active run_id
        rid = list(runtime.runs.keys())[0]
        runtime.runs[rid]["status"] = "paused"
        return {"type": "action", "next_agent": "maintainer", "instruction": "Step"}
    
    runtime._decide.side_effect = side_effect_with_pause
    
    result = await runtime.run_autonomous(agent_id="maintainer", goal="Long task", max_steps=5, cooldown=0)
    
    assert "paused" in result.message
    run_id = list(runtime.runs.keys())[0]
    
    # Now resume
    runtime._decide.side_effect = [{"type": "final", "message": "Resumed and finished"}]
    # Reset runs dict to simulate a new instance or cleared memory
    runtime.runs = {}
    
    result_resume = await runtime.run_autonomous(resume_run_id=run_id, max_steps=5, cooldown=0)
    assert result_resume.success is True
    assert "Resumed and finished" in result_resume.message
