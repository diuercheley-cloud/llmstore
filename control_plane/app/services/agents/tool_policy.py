# Owner: agent-platform
import uuid
from typing import Optional

from app.models.agents import AgentRegistryEntry, AgentTool
from sqlalchemy.ext.asyncio import AsyncSession


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
    if not tool.enabled:
        return PolicyDecision(allowed=False, reason="tool_disabled")

    if not agent and not agent_id:
        requires_approval = False if is_dry_run else bool(getattr(tool, "requires_approval", False))
        if not is_dry_run and getattr(tool, "side_effect_level", "none") == "destructive":
            requires_approval = True
        return PolicyDecision(
            allowed=True,
            reason="No agent context; applying direct tool policy path",
            requires_approval=requires_approval,
        )

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
