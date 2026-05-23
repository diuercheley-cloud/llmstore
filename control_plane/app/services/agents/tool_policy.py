# Owner: agent-platform
import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentTool, AgentRegistryEntry, AgentToolPermission


class PolicyDecision:
    def __init__(self, allowed: bool, reason: str, requires_approval: bool = False):
        self.allowed = allowed
        self.reason = reason
        self.requires_approval = requires_approval

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_approval": self.requires_approval
        }


async def evaluate_tool_policy(
    db: AsyncSession,
    tool: AgentTool,
    agent: Optional[AgentRegistryEntry] = None,
    agent_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[str] = None,
    is_dry_run: bool = False,
    run_id: Optional[uuid.UUID] = None
) -> PolicyDecision:
    """Evaluates tool execution using the unified Policy Engine v2."""
    from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyRequest
    
    policy_engine = AgentPolicyEngine(db)
    req_agent_id = agent_id or (agent.agent_id if agent else tool.owner_agent_id if hasattr(tool, "owner_agent_id") else uuid.UUID(int=0))
    
    req = PolicyRequest(
        action_type="tool_call",
        subject=tool.name,
        tenant_id=tenant_id or "default",
        agent_id=req_agent_id,
        run_id=run_id,
        context={"is_dry_run": is_dry_run}
    )
    
    decision = await policy_engine.evaluate_action_v2(req)
    
    return PolicyDecision(
        allowed=decision.result != "deny",
        reason=decision.reason or "Policy evaluated",
        requires_approval=decision.result == "require_approval"
    )
