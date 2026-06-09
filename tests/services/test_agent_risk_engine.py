from types import SimpleNamespace

from app.services.agents.agent_risk_engine import AgentRiskEngine


def test_agent_risk_engine_handles_missing_level_and_destructive_tasks():
    engine = AgentRiskEngine()
    agent = SimpleNamespace(risk_level=None, allowed_tools=["read"], max_steps=10, max_cost_brl=0)

    assert engine.calculate_agent_risk(agent) == 4
    assert engine.calculate_task_risk({"task_type": "tool_call", "tool_name": "delete_file"}) == 50
    assert engine.is_high_risk(50)
