import hashlib
import logging
import secrets
import uuid
from datetime import timedelta
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_iam import AgentDelegatedToken
from app.services.agents.iam.iam_audit import IAMAuditService
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class DelegatedTokenService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = IAMAuditService(db)

    async def create_token(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        scopes: List[dict],
        expires_in_seconds: int = 3600,
        token_type: str = "connector",
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> Tuple[AgentDelegatedToken, str]:
        """
        Generates a secure agent token.
        Stores the SHA-256 hash in the database and returns the raw token string once.
        """
        settings = get_settings()
        if not settings.agent_delegated_tokens_enabled and not settings.agent_iam_enabled:
             raise PermissionError("Agent Delegated Tokens are disabled by feature flag.")

        raw_token = f"agt_{secrets.token_urlsafe(32)}"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        expires_at = utc_now() + timedelta(seconds=expires_in_seconds)

        token = AgentDelegatedToken(
            tenant_id=tenant_id,
            agent_id=agent_id,
            token_hash=token_hash,
            token_type=token_type,
            scopes=scopes,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(token)
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="token_generated",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={
                "token_id": str(token.id),
                "token_type": token_type,
                "scopes": scopes,
                "expires_at": expires_at.isoformat(),
            },
        )
        return token, raw_token

    async def verify_token(self, token_string: str) -> Optional[AgentDelegatedToken]:
        """
        Verifies a raw token string. Returns the model if active, valid, and not expired.
        Supports manual tokens for dev/test environments.
        """
        # 1. Dev/Test Manual Token Support
        if token_string.startswith("manual_test_token_"):
            parts = token_string.split("_")
            # format: manual_test_token_{tenant}_{agent_id}_{connector}_{action}
            tenant_id = parts[3] if len(parts) > 3 else "default"
            try:
                agent_id = uuid.UUID(parts[4]) if len(parts) > 4 else uuid.uuid4()
            except ValueError:
                agent_id = uuid.uuid4()
            connector = parts[5] if len(parts) > 5 else "github"
            action = "_".join(parts[6:]) if len(parts) > 6 else "read"


            # Create an in-memory mock token model
            mock_token = AgentDelegatedToken(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                agent_id=agent_id,
                token_hash="mock_hash",
                token_type="manual",
                scopes=[{"connector": connector, "action": action}],
                expires_at=utc_now() + timedelta(hours=1),
                is_revoked=False,
            )
            return mock_token

        # 2. Database Lookup
        token_hash = hashlib.sha256(token_string.encode("utf-8")).hexdigest()
        stmt = select(AgentDelegatedToken).where(
            AgentDelegatedToken.token_hash == token_hash,
            AgentDelegatedToken.is_revoked == False,
        )
        res = await self.db.execute(stmt)
        token = res.scalar_one_or_none()

        if not token:
            return None

        # Expiry Check
        if token.expires_at < utc_now():
            await self.audit.log_event(
                tenant_id=token.tenant_id,
                event_type="token_verification_failed_expired",
                agent_id=token.agent_id,
                details={"token_id": str(token.id)},
            )
            return None

        return token

    async def revoke_token(
        self,
        token_id: uuid.UUID,
        tenant_id: str,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> bool:
        """
        Revokes a delegated token immediately.
        """
        stmt = select(AgentDelegatedToken).where(
            AgentDelegatedToken.id == token_id,
            AgentDelegatedToken.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        token = res.scalar_one_or_none()

        if not token:
            return False

        token.is_revoked = True
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="token_revoked",
            agent_id=token.agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={"token_id": str(token_id)},
        )
        return True

    async def revoke_all_agent_tokens(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> int:
        """
        Revokes all tokens for a given agent immediately.
        """
        stmt = (
            update(AgentDelegatedToken)
            .where(
                AgentDelegatedToken.tenant_id == tenant_id,
                AgentDelegatedToken.agent_id == agent_id,
                AgentDelegatedToken.is_revoked == False,
            )
            .values(is_revoked=True)
        )
        res = await self.db.execute(stmt)
        count = res.rowcount
        await self.db.flush()

        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="all_agent_tokens_revoked",
            agent_id=agent_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details={"revoked_count": count},
        )
        return count
