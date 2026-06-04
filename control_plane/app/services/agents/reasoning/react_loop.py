# Owner: agent-platform
import logging
from typing import Any, Dict, List

from app.services.agents.agent_llm_provider import AgentLLMProvider
from app.services.agents.reasoning.output_repair import OutputRepairService
from app.services.agents.reasoning.prompt_runtime import PromptRuntime
from app.services.agents.reasoning.structured_output import StructuredOutputValidator

logger = logging.getLogger(__name__)

class ReActLoop:
    """
    Implements the Thought/Action/Observation loop.
    """
    def __init__(self, llm_provider: AgentLLMProvider):
        self.llm_provider = llm_provider
        self.repair_svc = OutputRepairService(llm_provider)

    async def run(self, agent_def: Any, run: Any, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        # 1. Prepare ReAct prompt
        goal = run.input_text or "No goal specified"
        system_prompt = PromptRuntime.render_react_prompt(goal, tools)
        
        # In a real app, we'd inject this into the conversation history
        # For the prototype, we update instructions
        original_instructions = agent_def.instructions
        agent_def.instructions = f"{original_instructions}\n\n{system_prompt}"
        
        try:
            # 2. Call LLM for Thought and Action
            decision = await self.llm_provider.generate(agent_def, run, allowed_tools=[])
            
            # Sanitization: Extract Action and Thought
            content = decision.get("output") or ""
            
            thought = ""
            action_json = ""
            
            if "Thought:" in content:
                thought = content.split("Thought:")[1].split("Action:")[0].strip()
            
            if "Action:" in content:
                action_json = content.split("Action:")[1].split("Final Answer:")[0].strip()
            
            # 3. Validate and Repair Action
            try:
                action = StructuredOutputValidator.parse_and_validate(action_json)
            except Exception as e:
                action = await self.repair_svc.repair_output(action_json, str(e), agent_def, run)
                if not action:
                    raise ValueError("Failed to repair malformed ReAct action")

            # 4. Return sanitized decision
            return {
                "type": "tool_call",
                "thought_summary": thought, # Sanitize: don't log raw CoT if requested
                "tool_name": action.get("tool_name"),
                "tool_input": action.get("parameters"),
                "usage": decision.get("usage")
            }
        finally:
            agent_def.instructions = original_instructions
