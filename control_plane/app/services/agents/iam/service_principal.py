import logging
import secrets
import uuid

from app.core.config import get_settings
from app.core.security import hash_secret, verify_secret
from app.models.agents.agent_iam import AgentServicePrincipal
from app.services.agents.iam.iam_audit import IAMAuditService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ServicePrincipalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = IAMAuditService(db)

    async def create_service_principal(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        description: str | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> tuple[AgentServicePrincipal, str]:
        """
        Creates a new service principal for an agent.
        Generates a secure client ID and client secret, storing the secret's hash.
        Returns the created DB model and the raw client secret.
        """
        settings = get_settings()
        if not settings.agent_service_principals_enabled and not settings.agent_iam_enabled:
            raise PermissionError("Agent Service Principals are disabled by feature flag.")

        # Check if already exists
        stmt = select(AgentServicePrincipal).where(
            AgentServicePrincipal.tenant_id == tenant_id,
            AgentServicePrincipal.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            raise ValueError("Service Principal already exists for this agent.")

        client_id = f"sp-{uuid.uuid4().hex[:16]}"
        raw_secret = f"sec_{secrets.token_urlsafe(32)}"
        hashed_secret = hash_secret(raw_secret)

        sp = AgentServicePrincipal(
            tenant_id=tenant_id,
            agent_id=agent_id,
            client_id=client_id,
            client_secret_hash=hashed_secret,
            description=description,
            status="active",
        )
        self.db.add(sp)
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="service_principal_created",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "client_id": client_id,
                "description": description,
            },
        )
        return sp, raw_secret

    async def get_service_principal(
        self, tenant_id: str, agent_id: uuid.UUID
    ) -> AgentServicePrincipal | None:
        stmt = select(AgentServicePrincipal).where(
            AgentServicePrincipal.tenant_id == tenant_id,
            AgentServicePrincipal.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def authenticate(
        self, client_id: str, client_secret: str
    ) -> AgentServicePrincipal | None:
        """
        Validates client_id and client_secret. Returns the Service Principal if valid.
        """
        stmt = select(AgentServicePrincipal).where(
            AgentServicePrincipal.client_id == client_id,
            AgentServicePrincipal.status == "active",
        )
        res = await self.db.execute(stmt)
        sp = res.scalar_one_or_none()
        if not sp:
            return None

        if verify_secret(client_secret, sp.client_secret_hash):
            return sp
        return None

    async def rotate_secret(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> str:
        """
        Rotates the client secret for an agent's service principal.
        Returns the new raw secret.
        """
        sp = await self.get_service_principal(tenant_id, agent_id)
        if not sp:
            raise ValueError("Service Principal not found for this agent.")

        raw_secret = f"sec_{secrets.token_urlsafe(32)}"
        sp.client_secret_hash = hash_secret(raw_secret)
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="service_principal_secret_rotated",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "client_id": sp.client_id,
            },
        )
        return raw_secret

    async def suspend_service_principal(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> None:
        sp = await self.get_service_principal(tenant_id, agent_id)
        if not sp:
            raise ValueError("Service Principal not found for this agent.")

        sp.status = "suspended"
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="service_principal_suspended",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "client_id": sp.client_id,
            },
        )
