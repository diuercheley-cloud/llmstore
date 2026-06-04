import logging
import uuid
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_iam import AgentDelegatedToken, AgentTokenGrant
from app.services.agents.iam.delegated_tokens import DelegatedTokenService
from app.services.agents.iam.iam_audit import IAMAuditService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class TokenExchangeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_service = DelegatedTokenService(db)
        self.audit = IAMAuditService(db)

    async def create_token_grant(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        user_id: str,
        connector_id: Optional[str],
        scopes: List[str],
        expires_at: Optional[float] = None,  # epoch seconds or DateTime
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> AgentTokenGrant:
        """
        Creates a user-delegated token grant permitting an agent to access a connector with specific scopes.
        """
        expires_dt = None
        if expires_at:
            from datetime import timezone
            expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)

        grant = AgentTokenGrant(
            tenant_id=tenant_id,
            agent_id=agent_id,
            user_id=user_id,
            connector_id=connector_id,
            scopes=scopes,
            expires_at=expires_dt,
            is_revoked=False,
        )
        self.db.add(grant)
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="token_grant_created",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "grant_id": str(grant.id),
                "user_id": user_id,
                "connector_id": connector_id,
                "scopes": scopes,
            },
        )
        return grant

    async def revoke_token_grant(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        grant_id: uuid.UUID,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> bool:
        stmt = select(AgentTokenGrant).where(
            AgentTokenGrant.id == grant_id,
            AgentTokenGrant.tenant_id == tenant_id,
            AgentTokenGrant.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        grant = res.scalar_one_or_none()

        if not grant:
            return False

        grant.is_revoked = True
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="token_grant_revoked",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={"grant_id": str(grant_id)},
        )
        return True

    async def exchange_grant_for_token(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        user_id: str,
        connector_id: str,
        requested_scopes: List[str],
        expires_in_seconds: int = 3600,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> Tuple[AgentDelegatedToken, str]:
        """
        Exchange a user grant for an expiring, scoped AgentDelegatedToken.
        """
        settings = get_settings()
        if not settings.agent_oauth_on_behalf_of_enabled and not settings.agent_iam_enabled:
             raise PermissionError("On-Behalf-Of token exchange is disabled by feature flag.")

        # Find matching active grants for user, agent, tenant, and connector (or wildcard/null)
        stmt = select(AgentTokenGrant).where(
            AgentTokenGrant.tenant_id == tenant_id,
            AgentTokenGrant.agent_id == agent_id,
            AgentTokenGrant.user_id == user_id,
            AgentTokenGrant.is_revoked == False,
        )
        res = await self.db.execute(stmt)
        grants = res.scalars().all()

        matching_grant = None
        for g in grants:
            # check expiry
            if g.expires_at and g.expires_at < utc_now():
                continue

            # check connector ID matches (None/null acts as global/all connectors)
            if g.connector_id is None or g.connector_id.lower() == connector_id.lower():
                # check if grant scopes cover requested scopes
                if all(scope in g.scopes for scope in requested_scopes):
                    matching_grant = g
                    break

        if not matching_grant:
            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="token_exchange_failed_no_grant",
                agent_id=agent_id,
                details={
                    "user_id": user_id,
                    "connector_id": connector_id,
                    "requested_scopes": requested_scopes,
                },
            )
            raise PermissionError(
                f"No active delegated grant found for user '{user_id}' matching requested connector '{connector_id}' and scopes {requested_scopes}"
            )

        # Build list of scope dicts: [{"connector": connector_id, "action": scope}] for each requested scope
        # Or simple scope mapping
        token_scopes = [{"connector": connector_id, "action": s} for s in requested_scopes]

        token, raw_token = await self.token_service.create_token(
            tenant_id=tenant_id,
            agent_id=agent_id,
            scopes=token_scopes,
            expires_in_seconds=expires_in_seconds,
            token_type="connector",
            actor_id=actor_id,
            actor_type=actor_type,
        )

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="token_exchanged_success",
            agent_id=agent_id,
            actor_id=user_id,
            actor_type="user",
            details={
                "grant_id": str(matching_grant.id),
                "token_id": str(token.id),
                "connector_id": connector_id,
                "scopes": requested_scopes,
            },
        )

        return token, raw_token
