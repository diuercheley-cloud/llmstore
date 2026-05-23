# Owner: agent-platform
import logging
from typing import Any, Dict, List, Optional
from app.core.config import get_settings
from app.services.agents.agent_llm_provider import AgentLLMProvider
from app.services.agents.reasoning.react_loop import ReActLoop
from app.services.agents.reasoning.plan_and_solve_loop import PlanAndSolveLoop
from app.services.agents.reasoning.semantic_model_fallback import SemanticModelFallback

logger = logging.getLogger(__name__)

class ReasoningLoop:
    """
    Orchestrator for different reasoning strategies.
    """
    def __init__(self, llm_provider: AgentLLMProvider):
        self.llm_provider = llm_provider
        self.settings = get_settings()
        self.react = ReActLoop(llm_provider)
        self.plan_solve = PlanAndSolveLoop(llm_provider)
        self.fallback = SemanticModelFallback()

    async def execute(self, agent_def: Any, run: Any, allowed_tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.settings.agent_reasoning_loop_enabled:
            # Fallback to standard model call
            return await self.llm_provider.generate(agent_def, run, allowed_tools or [])

        try:
            decision = {}
            if self.settings.agent_plan_and_solve_enabled:
                decision = await self.plan_solve.run(agent_def, run)
            elif self.settings.agent_react_loop_enabled:
                decision = await self.react.run(agent_def, run, allowed_tools or [])
            else:
                # Default to standard model call
                decision = await self.llm_provider.generate(agent_def, run, allowed_tools or [])
            
            # Sanitization of CoT for privacy
            if "thought_summary" in decision:
                logger.info(f"Reasoning summary: {decision['thought_summary']}")
                # We can store this in observability or receipts
            
            return decision
        except Exception as e:
            logger.warning(f"Reasoning loop failure: {str(e)}")
            
            # Semantic Fallback
            fallback_model = await self.fallback.get_fallback_model(agent_def.model_id, str(e))
            if fallback_model:
                logger.info(f"Retrying with fallback model: {fallback_model}")
                agent_def.model_id = fallback_model
                return await self.execute(agent_def, run, allowed_tools)
            
            raise
