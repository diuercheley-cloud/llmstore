import uuid
import logging
from typing import Any, Dict, List, Optional
from app.models.agents import AgentDefinition, AgentTask

logger = logging.getLogger(__name__)

class AgentRiskEngine:
    """
    Engine to calculate and evaluate risk scores for agents and their actions.
    """
    
    RISK_LEVEL_WEIGHTS = {
        "low": 1,
        "medium": 5,
        "high": 20,
        "critical": 100
    }

    def calculate_agent_risk(self, agent: AgentDefinition) -> float:
        """
        Calculates a baseline risk score for an agent definition.
        """
        base_score = self.RISK_LEVEL_WEIGHTS.get(agent.risk_level.lower(), 1)
        
        # Adjust based on tools
        tool_count = len(agent.allowed_tools or [])
        tool_score = tool_count * 2
        
        # Adjust based on limits
        max_steps = agent.max_steps if agent.max_steps is not None else 10
        limit_score = (max_steps / 10.0) + (agent.max_cost_brl or 0)
        
        total_score = base_score + tool_score + limit_score
        return total_score

    def calculate_task_risk(self, task: Dict[str, Any]) -> float:
        """
        Calculates risk score for a specific task/action.
        """
        task_type = task.get("task_type", "model_call")
        base_score = 1.0
        
        if task_type == "tool_call":
            base_score = 10.0
            tool_name = task.get("tool_name", "")
            # Destructive tools check
            if any(p in tool_name.lower() for p in ["delete", "drop", "purge", "terminate"]):
                base_score *= 5.0
        
        elif task_type == "memory_write":
            base_score = 5.0
            
        return base_score

    def is_high_risk(self, score: float) -> bool:
        return score >= 20.0

    def calculate_risk_level(self, agent: AgentDefinition) -> str:
        score = self.calculate_agent_risk(agent)
        if score >= 100: return "critical"
        if score >= 50: return "high"
        if score >= 10: return "medium"
        return "low"
