# Owner: agent-platform
import json
import logging
from typing import Any, Dict, Optional

from app.services.agents.agent_llm_provider import AgentLLMProvider

logger = logging.getLogger(__name__)

class OutputRepairService:
    """
    Handles retries and repair prompts for malformed JSON or invalid structured outputs.
    """
    def __init__(self, llm_provider: AgentLLMProvider):
        self.llm_provider = llm_provider

    async def repair_output(
        self, 
        original_output: str, 
        error: str, 
        agent_def: Any, 
        run: Any, 
        max_attempts: int = 2
    ) -> Optional[Dict[str, Any]]:
        from app.services.agents.reasoning.structured_output import StructuredOutputValidator
        
        current_output = original_output
        current_error = error
        
        for attempt in range(max_attempts):
            logger.info(f"Attempting output repair (attempt {attempt + 1}/{max_attempts})")
            
            repair_prompt = (
                f"The previous output was invalid. Error: {current_error}\n"
                f"Original output: {current_output}\n"
                f"Please provide the corrected output in valid JSON format ONLY."
            )
            
            # Create a temporary agent definition for the repair
            # This is a bit hacky, ideally we have a dedicated method for repair
            repair_agent_def = MagicMock() if hasattr(agent_def, "mock") else agent_def 
            # In a real app we'd clone and update instructions
            
            try:
                # Call LLM with repair instructions
                # Simplified: prepend repair prompt to instructions
                original_instructions = agent_def.instructions
                agent_def.instructions = f"{original_instructions}\n\n[REPAIR INSTRUCTION]\n{repair_prompt}"
                
                decision = await self.llm_provider.generate(agent_def, run, allowed_tools=[])
                agent_def.instructions = original_instructions # Restore
                
                # Check if decision contains the repaired content
                content = decision.get("output") or json.dumps(decision)
                
                return StructuredOutputValidator.parse_and_validate(content)
            except Exception as e:
                current_error = str(e)
                logger.warning(f"Repair attempt {attempt + 1} failed: {current_error}")
                
        return None

from unittest.mock import MagicMock
