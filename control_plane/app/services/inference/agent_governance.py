import hashlib
import json
import uuid
from typing import Any, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...core.config import get_settings
from ...models.commercial_agents import (
    CommercialAgentDelegationPolicy,
    CommercialAgentExecution,
    CommercialAgentMemoryBoundary,
    CommercialAgentProfile,
    CommercialAgentToolExecution,
)


async def create_agent_profile(
    db: AsyncSession,
    agent_name: str,
    client_id: Optional[str] = None,
    allowed_tools: List[str] = [],
    can_delegate: bool = False
) -> CommercialAgentProfile:
    profile = CommercialAgentProfile(
        agent_name=agent_name,
        client_id=client_id,
        allowed_tools=allowed_tools,
        can_delegate=can_delegate
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

async def start_agent_execution(
    db: AsyncSession,
    agent_id: uuid.UUID,
    session_id: str,
    input_text: str,
    parent_execution_id: Optional[uuid.UUID] = None
) -> CommercialAgentExecution:
    input_hash = hashlib.sha256(input_text.encode()).hexdigest()
    execution = CommercialAgentExecution(
        agent_id=agent_id,
        session_id=session_id,
        input_hash=input_hash,
        parent_execution_id=parent_execution_id,
        status="running"
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution

async def authorize_tool_execution(
    db: AsyncSession,
    execution_id: uuid.UUID,
    tool_name: str,
    tool_input: Any
) -> Tuple[bool, str]:
    # 1. Resolve execution and profile
    res = await db.execute(
        select(CommercialAgentExecution, CommercialAgentProfile)
        .join(CommercialAgentProfile, CommercialAgentExecution.agent_id == CommercialAgentProfile.id)
        .where(CommercialAgentExecution.id == execution_id)
    )
    row = res.one_or_none()
    if not row:
        return False, "Execution not found"
    
    execution, profile = row
    
    # 2. Check if tool is allowed
    allowed_tools = profile.allowed_tools or []
    if tool_name not in allowed_tools and "*" not in allowed_tools:
        return False, f"Tool '{tool_name}' not in agent's allow-list"
        
    # 3. Check for mandatory approval
    approval = "auto"
    if profile.requires_approval_for_tools:
        approval = "pending"
        
    # 4. Log tool execution
    tool_exec = CommercialAgentToolExecution(
        execution_id=execution_id,
        tool_name=tool_name,
        input_hash=hashlib.sha256(json.dumps(tool_input).encode()).hexdigest(),
        approval_status=approval,
        is_confidential=profile.confidential_runtime_required
    )
    db.add(tool_exec)
    await db.commit()
    
    if approval == "pending":
        return False, f"Tool '{tool_name}' requires manual approval"
        
    return True, "Authorized"

async def check_delegation_allowed(
    db: AsyncSession,
    source_agent_id: uuid.UUID,
    target_agent_id: uuid.UUID
) -> bool:
    # 1. Check direct policy
    res = await db.execute(
        select(CommercialAgentDelegationPolicy).where(
            CommercialAgentDelegationPolicy.source_agent_id == source_agent_id,
            CommercialAgentDelegationPolicy.target_agent_id == target_agent_id,
            CommercialAgentDelegationPolicy.is_allowed == True
        )
    )
    policy = res.scalar_one_or_none()
    if policy:
        return True
        
    # 2. Check if source agent can delegate generally (governance fallback)
    source_res = await db.execute(select(CommercialAgentProfile).where(CommercialAgentProfile.id == source_agent_id))
    source = source_res.scalar_one_or_none()
    if source and source.can_delegate:
        # If no specific policy exists, allow if source has global delegation right
        return True
        
    return False

async def enforce_memory_boundary(
    db: AsyncSession,
    execution_id: uuid.UUID,
    tenant_id: str,
    boundary_type: str = "session"
) -> CommercialAgentMemoryBoundary:
    boundary = CommercialAgentMemoryBoundary(
        execution_id=execution_id,
        tenant_id=tenant_id,
        boundary_type=boundary_type
    )
    db.add(boundary)
    await db.commit()
    return boundary

async def summarize_agent_governance(db: AsyncSession) -> dict:
    profiles_count = await db.execute(select(CommercialAgentProfile))
    executions_count = await db.execute(select(CommercialAgentExecution))
    tool_count = await db.execute(select(CommercialAgentToolExecution))
    
    return {
        "enabled": get_settings().commercial_agent_governance_enabled,
        "mode": get_settings().commercial_agent_governance_mode,
        "total_profiles": len(profiles_count.scalars().all()),
        "total_executions": len(executions_count.scalars().all()),
        "tools_executed": len(tool_count.scalars().all())
    }
