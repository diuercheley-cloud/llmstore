# Owner: agent-platform
import uuid
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentDefinition, 
    AgentRun, 
    AgentEvalBaseline, 
    AgentMemoryPolicy, 
    AgentPolicyDecision
)
from app.services.agents.agent_risk_engine import AgentRiskEngine

logger = logging.getLogger(__name__)

class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_DRY_RUN = "require_dry_run"

class PolicyRequest(BaseModel):
    action_type: str  # tool_call|memory_read|memory_write|handoff|planner_exec
    subject: str      # tool name, memory type, target agent id, etc.
    tenant_id: str
    agent_id: uuid.UUID
    run_id: Optional[uuid.UUID] = None
    context: Dict[str, Any] = Field(default_factory=dict)

class AgentPolicyEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.risk_engine = AgentRiskEngine()

    async def evaluate_action_v2(self, request: PolicyRequest) -> AgentPolicyDecision:
        """
        Unified policy evaluation and recording.
        Mandatory flow: build Request -> Evaluate -> Record Decision.
        """
        # 1. Fetch Agent
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == request.agent_id))
        agent = res_agent.scalar_one_or_none()
        if not agent:
            return await self._record_decision(request, PolicyDecision.DENY, "Agent not found", "critical")

        risk_level = self.risk_engine.calculate_risk_level(agent)
        
        result = PolicyDecision.ALLOW
        reason = "Action permitted by default governance policy."

        # 2. Apply Rules by Action Type
        if request.action_type == "tool_call":
            result, reason = await self._check_tool_rules(agent, request)
        elif request.action_type == "memory_write":
            result, reason = await self._check_memory_rules(agent, request)
        elif request.action_type == "handoff":
            result, reason = await self._check_handoff_rules(agent, request)
        elif request.action_type == "planner_exec":
            result, reason = await self._check_planner_rules(agent, request)
        elif request.action_type == "memory_read":
             # Basic read check
             result = PolicyDecision.ALLOW
             reason = "Memory read permitted."

        # 3. Record Decision and return
        return await self._record_decision(request, result, reason, risk_level)

    async def _record_decision(self, req: PolicyRequest, result: PolicyDecision, reason: str, risk: str) -> AgentPolicyDecision:
        decision = AgentPolicyDecision(
            run_id=req.run_id,
            action_type=req.action_type,
            subject=req.subject,
            tenant_id=req.tenant_id,
            agent_id=req.agent_id,
            risk_level=risk,
            result=result.value,
            reason=reason,
            policy_version="1.1.0",
            created_at=utc_now()
        )
        self.db.add(decision)
        # Flush to get ID if needed, but don't commit yet
        await self.db.flush()
        return decision

    async def _check_tool_rules(self, agent: AgentDefinition, req: PolicyRequest) -> Tuple[PolicyDecision, str]:
        tool_name = req.subject
        
        # 1. Allowlist Check
        if agent.allowed_tools and tool_name not in agent.allowed_tools and "*" not in agent.allowed_tools:
            return PolicyDecision.DENY, f"Tool '{tool_name}' not in agent's allowlist."
        
        # 2. Destructive Tools Check
        if any(p in tool_name.lower() for p in ["delete", "drop", "purge", "terminate"]):
            return PolicyDecision.REQUIRE_APPROVAL, f"Destructive tool '{tool_name}' requires human approval."

        # 3. Category Restrictions
        if "shell" in tool_name.lower() or "terminal" in tool_name.lower():
             return PolicyDecision.DENY, "Shell/Terminal tools are globally restricted."

        return PolicyDecision.ALLOW, "Tool call permitted."

    async def _check_memory_rules(self, agent: AgentDefinition, req: PolicyRequest) -> Tuple[PolicyDecision, str]:
        memory_type = req.subject
        # Check for active policy
        res_policy = await self.db.execute(
            select(AgentMemoryPolicy).where(
                AgentMemoryPolicy.tenant_id == req.tenant_id,
                AgentMemoryPolicy.memory_type == memory_type
            )
        )
        if not res_policy.scalar_one_or_none():
            return PolicyDecision.DENY, f"Memory write denied: no active retention policy for '{memory_type}'."
        
        return PolicyDecision.ALLOW, "Memory persistence permitted."

    async def _check_handoff_rules(self, agent: AgentDefinition, req: PolicyRequest) -> Tuple[PolicyDecision, str]:
        target_agent_id = req.subject
        # Policy: high risk agents cannot handoff to non-production agents
        if self.risk_engine.calculate_agent_risk(agent) >= 50:
            res_target = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == uuid.UUID(target_agent_id)))
            target = res_target.scalar_one_or_none()
            if target and target.status != "active":
                return PolicyDecision.DENY, "High risk agent cannot handoff to a non-production agent."
                
        return PolicyDecision.ALLOW, "Handoff permitted."

    async def _check_planner_rules(self, agent: AgentDefinition, req: PolicyRequest) -> Tuple[PolicyDecision, str]:
        # Implementation for planner execution rules (e.g. max complexity)
        return PolicyDecision.ALLOW, "Planner execution permitted."

    # Legacy Compatibility Layer
    async def evaluate_agent_activation(self, agent: AgentDefinition) -> Tuple[PolicyDecision, str]:
        risk_score = self.risk_engine.calculate_agent_risk(agent)
        if risk_score >= 100 and not agent.owner:
            return PolicyDecision.DENY, "Critical risk agent must have an owner assigned."

        if agent.status == "active" and self.settings.agent_production_requires_eval_baseline:
            res = await self.db.execute(select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == agent.id))
            if not res.scalar_one_or_none():
                return PolicyDecision.DENY, "Agent requires an evaluation baseline for production activation."

        return PolicyDecision.ALLOW, "Activation permitted."

    async def evaluate_action(self, agent: AgentDefinition, run: AgentRun, action: Dict[str, Any]) -> Tuple[PolicyDecision, str]:
        req = PolicyRequest(
            action_type=action.get("task_type", "model_call"),
            subject=action.get("tool_name") or action.get("memory_type") or action.get("target_agent_id") or "default",
            tenant_id=run.tenant_id,
            agent_id=agent.id,
            run_id=run.id,
            context=action
        )
        decision = await self.evaluate_action_v2(req)
        return PolicyDecision(decision.result), decision.reason

    async def simulate_action(self, agent_id: uuid.UUID, action: Dict[str, Any]) -> Dict[str, Any]:
        res_agent = await self.db.execute(select(AgentDefinition).where(AgentDefinition.id == agent_id))
        agent = res_agent.scalar_one_or_none()
        if not agent:
            return {"decision": PolicyDecision.DENY, "reason": "Agent not found"}
        
        req = PolicyRequest(
            action_type=action.get("task_type", "model_call"),
            subject=action.get("tool_name") or "default",
            tenant_id="sim-tenant",
            agent_id=agent_id,
            context=action
        )
        decision = await self.evaluate_action_v2(req)
        return {
            "decision": decision.result,
            "reason": decision.reason,
            "simulated": True
        }
