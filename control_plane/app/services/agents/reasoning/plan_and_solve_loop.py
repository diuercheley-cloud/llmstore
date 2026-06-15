# Owner: agent-platform
import logging
from typing import Any

from app.services.agents.agent_llm_provider import AgentLLMProvider

logger = logging.getLogger(__name__)


class PlanAndSolveLoop:
    """
    Implements the Plan-and-Solve orchestration.
    """

    def __init__(self, llm_provider: AgentLLMProvider):
        self.llm_provider = llm_provider

    async def run(self, agent_def: Any, run: Any) -> dict[str, Any]:
        # 1. Generate Plan
        # (Mocked plan generation)
        plan_decision = await self.llm_provider.generate(agent_def, run, allowed_tools=[])

        # 2. Extract and Validate Plan
        # In a real app, we'd use StructuredOutputValidator with a Plan model
        plan = {
            "goal": run.input_text,
            "tasks": [
                {
                    "title": "Research",
                    "task_type": "tool_call",
                    "input_data": {"tool_name": "search"},
                },
                {"title": "Summarize", "task_type": "model_reasoning", "input_data": {}},
            ],
        }

        # 3. Trigger TaskEngine (Orchestration handled by AgentExecutor after this return)
        return {
            "type": "planning",
            "goal": plan["goal"],
            "tasks": plan["tasks"],
            "usage": plan_decision.get("usage"),
        }
