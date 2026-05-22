import uuid
import logging
from typing import Optional, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentMemoryPolicy
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class MemoryPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_policy(self, tenant_id: str, agent_id: Optional[uuid.UUID], memory_type: str) -> Optional[AgentMemoryPolicy]:
        # Specific policy for agent
        stmt = select(AgentMemoryPolicy).where(
            AgentMemoryPolicy.tenant_id == tenant_id,
            AgentMemoryPolicy.agent_id == agent_id,
            AgentMemoryPolicy.memory_type == memory_type
        )
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()
        
        if not policy and agent_id is not None:
            # Fallback to tenant-level policy for this memory type
            stmt = select(AgentMemoryPolicy).where(
                AgentMemoryPolicy.tenant_id == tenant_id,
                AgentMemoryPolicy.agent_id.is_(None),
                AgentMemoryPolicy.memory_type == memory_type
            )
            res = await self.db.execute(stmt)
            policy = res.scalar_one_or_none()
            
        return policy

    async def create_policy(self, data: dict) -> AgentMemoryPolicy:
        policy = AgentMemoryPolicy(
            tenant_id=data["tenant_id"],
            agent_id=data.get("agent_id"),
            memory_type=data["memory_type"],
            retention_days=data.get("retention_days", 30),
            redaction_enabled=data.get("redaction_enabled", True),
            encryption_required=data.get("encryption_required", False),
            allow_export=data.get("allow_export", False)
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def list_policies(self, tenant_id: str) -> List[AgentMemoryPolicy]:
        stmt = select(AgentMemoryPolicy).where(AgentMemoryPolicy.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
