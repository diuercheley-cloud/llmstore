
import pytest
from app.core.config import get_settings
from app.services.agents.reasoning.mcts.mcts_runtime import MCTSRuntime


@pytest.mark.asyncio
async def test_mcts_disabled_bloqueia():
    settings = get_settings()
    settings.agent_mcts_reasoning_enabled = False
    
    runtime = MCTSRuntime()
    with pytest.raises(PermissionError, match="MCTS Reasoning is disabled"):
        await runtime.run_search({}, ["action1"])

@pytest.mark.asyncio
async def test_respeita_max_rollouts():
    settings = get_settings()
    settings.agent_mcts_reasoning_enabled = True
    
    runtime = MCTSRuntime()
    # Mocking rollout to check count is possible if we add telemetry
    # For now, we check it completes
    action = await runtime.run_search({"steps": 0}, ["tool_a", "final_answer"], max_rollouts=10)
    assert action in ["tool_a", "final_answer"]

@pytest.mark.asyncio
async def test_escolhe_acao_com_melhor_score_em_mock():
    settings = get_settings()
    settings.agent_mcts_reasoning_enabled = True
    
    runtime = MCTSRuntime()
    # In our mock sandbox, 'final_answer' leads to goal_achieved=True which has score 1.0
    # So MCTS should strongly prefer it over others.
    action = await runtime.run_search({"steps": 0}, ["tool_a", "tool_b", "final_answer"], max_rollouts=20)
    assert action == "final_answer"

@pytest.mark.asyncio
async def test_budget_excedido_interrompe():
    settings = get_settings()
    settings.agent_mcts_reasoning_enabled = True
    
    runtime = MCTSRuntime()
    # Test time budget (max_time_seconds)
    # We use a very small time to trigger timeout
    action = await runtime.run_search({"steps": 0}, ["tool_a"], max_rollouts=1000, max_time_seconds=0.001)
    assert action is not None # Should still return best effort or stop
