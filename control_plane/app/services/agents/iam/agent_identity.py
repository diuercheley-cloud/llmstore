import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_iam import AgentIdentityBinding
from app.services.agents.iam.iam_audit import IAMAuditService

logger = logging.getLogger(__name__)

class AgentIdentityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = IAMAuditService(db)

    async def bind_identity(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        identity_provider: str = "internal",
        external_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> AgentIdentityBinding:
        """
        Creates or updates a tenant-scoped sovereign identity binding for an agent.
        """
        stmt = select(AgentIdentityBinding).where(
            AgentIdentityBinding.tenant_id == tenant_id,
            AgentIdentityBinding.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        binding = res.scalar_one_or_none()

        if binding:
            binding.identity_provider = identity_provider
            binding.external_id = external_id
            binding.identity_metadata = metadata or {}
            event_type = "agent_identity_updated"
        else:
            binding = AgentIdentityBinding(
                tenant_id=tenant_id,
                agent_id=agent_id,
                identity_provider=identity_provider,
                external_id=external_id,
                identity_metadata=metadata or {},
            )
            self.db.add(binding)
            event_type = "agent_identity_created"

        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type=event_type,
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "identity_provider": identity_provider,
                "external_id": external_id,
            },
        )
        return binding

    async def get_identity_binding(
        self, tenant_id: str, agent_id: uuid.UUID
    ) -> Optional[AgentIdentityBinding]:
        stmt = select(AgentIdentityBinding).where(
            AgentIdentityBinding.tenant_id == tenant_id,
            AgentIdentityBinding.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def has_identity(self, tenant_id: str, agent_id: uuid.UUID) -> bool:
        """
        Checks if the agent has a bound sovereign identity.
        """
        binding = await self.get_identity_binding(tenant_id, agent_id)
        return binding is not None
