import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import (
    AgentDelegationPolicy, 
    AgentSharedMemoryPolicy, 
    AgentCollaborationSession,
    AgentRun,
    AgentDefinition,
    AgentTraceLink
)
from app.core.time import utc_now
from app.services.admin_rbac import record_admin_audit_event

logger = logging.getLogger(__name__)

class MultiAgentGovernanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_delegation_allowed(
        self, 
        tenant_id: str, 
        source_agent_id: uuid.UUID, 
        target_agent_id: uuid.UUID
    ) -> Tuple[bool, str]:
        # Rule: Cross-tenant blocked
        # (Assuming source and target are looked up or passed correctly)
        source = await self.db.get(AgentDefinition, source_agent_id)
        target = await self.db.get(AgentDefinition, target_agent_id)

        if not source or not target:
            return False, "Agent not found"
        
        if source.tenant_id != target.tenant_id or source.tenant_id != tenant_id:
            return False, "Cross-tenant delegation is strictly prohibited"

        # Rule: Explicit policy source->target
        res = await self.db.execute(
            select(AgentDelegationPolicy).where(
                AgentDelegationPolicy.tenant_id == tenant_id,
                AgentDelegationPolicy.source_agent_id == source_agent_id,
                AgentDelegationPolicy.target_agent_id == target_agent_id,
                AgentDelegationPolicy.is_active == True
            )
        )
        policy = res.scalar_one_or_none()
        if not policy:
            return False, f"No active delegation policy found from {source.name} to {target.name}"

        return True, "Delegation allowed"

    async def check_shared_memory_access(
        self, 
        tenant_id: str, 
        agent_id: uuid.UUID, 
        group_id: str, 
        action: str = "read"
    ) -> bool:
        res = await self.db.execute(
            select(AgentSharedMemoryPolicy).where(
                AgentSharedMemoryPolicy.tenant_id == tenant_id,
                AgentSharedMemoryPolicy.agent_id == agent_id,
                AgentSharedMemoryPolicy.agent_group_id == group_id
            )
        )
        policy = res.scalar_one_or_none()
        if not policy:
            return False
        
        if action == "read":
            return policy.can_read
        if action == "write":
            return policy.can_write
        return False

    async def detect_delegation_loop(self, run_id: uuid.UUID, target_agent_id: uuid.UUID) -> bool:
        # Trace back the chain of AgentTraceLink with link_reason="handoff"
        visited_agents = {target_agent_id}
        current_run_id = run_id
        
        # Max depth safety
        for _ in range(20):
            res = await self.db.execute(
                select(AgentRun).where(AgentRun.id == current_run_id)
            )
            run = res.scalar_one_or_none()
            if not run:
                break
            
            if run.agent_id in visited_agents:
                return True # Loop detected
            
            visited_agents.add(run.agent_id)
            
            # Find the parent run
            res_link = await self.db.execute(
                select(AgentTraceLink).where(
                    AgentTraceLink.linked_trace_id == str(current_run_id),
                    AgentTraceLink.link_reason == "handoff"
                )
            )
            link = res_link.scalar_one_or_none()
            if not link:
                break
            
            current_run_id = link.run_id
            
        return False

    async def create_collaboration_session(self, root_run_id: uuid.UUID, tenant_id: str) -> AgentCollaborationSession:
        session = AgentCollaborationSession(
            tenant_id=tenant_id,
            root_run_id=root_run_id,
            status="active"
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_full_trace(self, session_id: uuid.UUID) -> List[Dict[str, Any]]:
        session = await self.db.get(AgentCollaborationSession, session_id)
        if not session:
            return []
        
        # BFS/DFS traversal of the execution tree starting from root_run_id
        # For simplicity, we'll return a flat list of related runs
        results = []
        queue = [session.root_run_id]
        visited = set()
        
        while queue:
            run_id = queue.pop(0)
            if run_id in visited: continue
            visited.add(run_id)
            
            run = await self.db.get(AgentRun, run_id)
            if run:
                results.append({
                    "run_id": str(run.id),
                    "agent_id": str(run.agent_id),
                    "status": run.status,
                    "started_at": run.started_at.isoformat()
                })
                
                # Find children
                res_links = await self.db.execute(
                    select(AgentTraceLink).where(AgentTraceLink.run_id == run_id)
                )
                for link in res_links.scalars().all():
                    try:
                        child_id = uuid.UUID(link.linked_trace_id)
                        queue.append(child_id)
                    except:
                        pass
        return results
