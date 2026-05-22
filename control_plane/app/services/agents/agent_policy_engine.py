import uuid
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun, AgentEvalBaseline, AgentMemoryPolicy
from app.services.agents.agent_risk_engine import AgentRiskEngine

logger = logging.getLogger(__name__)

class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_DRY_RUN = "require_dry_run"
    REQUIRE_HANDOFF = "require_handoff"
    REQUIRE_REPLAN = "require_replan"

class AgentPolicyEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.risk_engine = AgentRiskEngine()

    async def evaluate_agent_activation(self, agent: AgentDefinition) -> Tuple[PolicyDecision, str]:
        """
        Policy: no_production_agent_without_eval_baseline
        Policy: no_high_risk_agent_without_owner
        """
        # High risk must have owner
        risk_score = self.risk_engine.calculate_agent_risk(agent)
        if risk_score >= 50 and not agent.owner:
            return PolicyDecision.DENY, "High risk agent must have an owner assigned."

        # Production (active) must have baseline
        if agent.status == "active" and self.settings.agent_production_requires_eval_baseline:
            res = await self.db.execute(select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == agent.id))
            if not res.scalar_one_or_none():
                return PolicyDecision.DENY, "Agent requires an evaluation baseline to be activated in production."

        return PolicyDecision.ALLOW, "Agent activation permitted."

    async def evaluate_action(self, agent: AgentDefinition, run: AgentRun, action: Dict[str, Any]) -> Tuple[PolicyDecision, str]:
        """
        Evaluates a specific action (tool call, memory op, etc.)
        Policies: 
        - max_steps_by_risk
        - allowed_tools_by_agent
        - blocked_tools_by_environment
        - approval_required_for_destructive_tools
        - no_external_api_in_sovereign_mode
        - no_memory_write_without_policy
        - no_shell_tool_by_default
        """
        task_type = action.get("task_type", "model_call")
        
        # 1. max_steps_by_risk
        risk_score = self.risk_engine.calculate_agent_risk(agent)
        limit_steps = 50 if risk_score < 10 else 20 if risk_score < 50 else 10
        if run.total_steps >= limit_steps:
            return PolicyDecision.DENY, f"Action denied: max steps ({limit_steps}) reached for risk level."

        # 2. Tool policies
        if task_type == "tool_call":
            tool_name = action.get("tool_name", "")
            
            # no_shell_tool_by_default
            if "shell" in tool_name.lower() or "terminal" in tool_name.lower():
                return PolicyDecision.DENY, "Shell/Terminal tools are blocked by default governance policy."

            # allowed_tools_by_agent
            if agent.allowed_tools and tool_name not in agent.allowed_tools and "*" not in agent.allowed_tools:
                return PolicyDecision.DENY, f"Tool '{tool_name}' is not in the allowed list for this agent."

            # approval_required_for_destructive_tools
            if any(p in tool_name.lower() for p in ["delete", "drop", "purge"]):
                return PolicyDecision.REQUIRE_APPROVAL, f"Destructive tool '{tool_name}' requires human approval."

            # no_external_api_in_sovereign_mode
            # Placeholder: assuming we can detect external tools
            if getattr(self.settings, "sovereign_mode", False) and action.get("is_external", False):
                return PolicyDecision.DENY, "External API calls are prohibited in sovereign mode."

        # 3. Memory policies
        if task_type == "memory_write":
            # no_memory_write_without_policy
            res_policy = await self.db.execute(
                select(AgentMemoryPolicy).where(
                    AgentMemoryPolicy.tenant_id == run.tenant_id,
                    AgentMemoryPolicy.memory_type == action.get("memory_type", "short_term")
                )
            )
            if not res_policy.scalar_one_or_none():
                return PolicyDecision.DENY, "Memory write denied: no active memory policy for this tenant/type."

        return PolicyDecision.ALLOW, "Action permitted by governance policy."

    async def simulate_action(self, agent_id: uuid.UUID, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates a policy decision without executing anything.
        """
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        agent = res_agent.scalar_one_or_none()
        if not agent:
            return {"decision": PolicyDecision.DENY, "reason": "Agent not found"}
        
        # Create a mock run for simulation
        mock_run = AgentRun(agent_id=agent_id, tenant_id="sim-tenant", total_steps=0)
        
        decision, reason = await self.evaluate_action(agent, mock_run, action)
        return {
            "decision": decision,
            "reason": reason,
            "simulated": True
        }
