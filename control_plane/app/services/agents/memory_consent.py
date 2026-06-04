"""
Owner: agent-platform
Status: beta
"""
import uuid
from typing import List, Optional

from app.core.time import utc_now
from app.models.agents import AgentMemoryConsent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class MemoryConsentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_consent(self, tenant_id: str, user_id: str, memory_type: str, agent_id: Optional[uuid.UUID] = None) -> Optional[AgentMemoryConsent]:
        stmt = select(AgentMemoryConsent).where(
            AgentMemoryConsent.tenant_id == tenant_id,
            AgentMemoryConsent.user_id == user_id,
            AgentMemoryConsent.memory_type == memory_type,
            AgentMemoryConsent.status == "active"
        )
        if agent_id:
            stmt = stmt.where(AgentMemoryConsent.agent_id == agent_id)
        else:
            stmt = stmt.where(AgentMemoryConsent.agent_id.is_(None))
            
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create_consent(self, tenant_id: str, user_id: str, memory_type: str, agent_id: Optional[uuid.UUID] = None) -> AgentMemoryConsent:
        # Check existing
        existing = await self.get_consent(tenant_id, user_id, memory_type, agent_id)
        if existing:
            return existing
            
        consent = AgentMemoryConsent(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=memory_type,
            agent_id=agent_id,
            status="active"
        )
        self.db.add(consent)
        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def list_consents(self, tenant_id: str) -> List[AgentMemoryConsent]:
        stmt = select(AgentMemoryConsent).where(AgentMemoryConsent.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def revoke_consent(self, tenant_id: str, consent_id: uuid.UUID):
        stmt = select(AgentMemoryConsent).where(
            AgentMemoryConsent.id == consent_id,
            AgentMemoryConsent.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        consent = res.scalar_one_or_none()
        if consent:
            consent.status = "revoked"
            consent.revoked_at = utc_now()
            await self.db.commit()
