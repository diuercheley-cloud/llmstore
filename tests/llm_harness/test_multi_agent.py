from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.multi_agent import MultiAgentOrchestrator


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_success():
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    
    orchestrator = MultiAgentOrchestrator(coding_loop)
    
    # Mock Planner
    orchestrator._call_planner = AsyncMock(return_value=[{"action_type": "plan", "message": "Go!"}])
    
    # Mock Coder
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": ["f1.py"]}
    ))
    
    # Mock Reviewer
    orchestrator._call_reviewer = AsyncMock(return_value={"status": "approved", "feedback": "Good"})
    
    result = await orchestrator.run_planner_coder_reviewer("Task X")
    
    assert result.success is True
    assert orchestrator._call_planner.called
    assert coding_loop.run.called
    assert orchestrator._call_reviewer.called

@pytest.mark.asyncio
async def test_multi_agent_orchestrator_revision():
    coding_loop = MagicMock()
    coding_loop.agent_client = MagicMock()
    
    orchestrator = MultiAgentOrchestrator(coding_loop)
    
    # Mock Planner
    orchestrator._call_planner = AsyncMock(return_value=[{"action_type": "plan", "message": "Go!"}])
    
    # Mock Coder
    coding_loop.run = AsyncMock(return_value=ExecutionResult(
        success=True, message="Done", metrics={"changed_files": ["f1.py"]}
    ))
    
    # Mock Reviewer: rejects first time, accepts second time
    orchestrator._call_reviewer = AsyncMock(side_effect=[
        {"status": "rejected", "feedback": "Fix Y"},
        {"status": "approved", "feedback": "Fixed"}
    ])
    
    result = await orchestrator.run_planner_coder_reviewer("Task X")
    
    assert result.success is True
    assert orchestrator._call_planner.call_count == 2
    assert coding_loop.run.call_count == 2
    assert orchestrator._call_reviewer.call_count == 2
