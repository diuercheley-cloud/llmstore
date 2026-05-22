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
    tenant_id: Optional[str] = None,
    is_dry_run: bool = False
) -> PolicyDecision:
    """Evaluates whether an agent or tenant is allowed to execute a registered tool."""
    
    # 1. Enforce Enablement
    if not tool.enabled:
        return PolicyDecision(allowed=False, reason="tool_disabled")

    # 5. Tool without dry_run cannot be used by an experimental agent
    if agent and agent.supported_surface_status == "experimental":
        if not tool.dry_run_supported:
            return PolicyDecision(allowed=False, reason="experimental_agent_restricted_no_dry_run")

    # Enforce RBAC Permissions
    # Fetch permissions for this tool
    stmt = select(AgentToolPermission).where(AgentToolPermission.agent_tool_id == tool.id)
    result = await db.execute(stmt)
    permissions = result.scalars().all()

    if permissions:
        # Caller must match at least one permission rule
        matched = False
        for perm in permissions:
            # Match tenant if specified in permission
            tenant_match = (perm.tenant_id is None or perm.tenant_id == tenant_id)
            # Match agent if specified in permission
            agent_match = (perm.agent_id is None or (agent and perm.agent_id == agent.agent_id))
            
            if tenant_match and agent_match:
                matched = True
                break
        
        if not matched:
            return PolicyDecision(allowed=False, reason="permission_denied")

    # Enforce Approval requirements
    if tool.requires_approval and not is_dry_run:
        return PolicyDecision(allowed=True, reason="approval_required", requires_approval=True)

    return PolicyDecision(allowed=True, reason="policy_allow")
