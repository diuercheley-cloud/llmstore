"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentEphemeralCredential
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class EphemeralCredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue_credential(
        self,
        run_id: uuid.UUID,
        scope: str,
        credential_type: str,
        value: str,
        ttl_minutes: int = 5
    ) -> AgentEphemeralCredential:
        cred = AgentEphemeralCredential(
            run_id=run_id,
            scope=scope,
            credential_type=credential_type,
            credential_value=value,
            expires_at=utc_now() + timedelta(minutes=ttl_minutes),
            created_at=utc_now()
        )
        self.db.add(cred)
        await self.db.commit()
        await self.db.refresh(cred)
        return cred

    async def get_valid_credential(self, run_id: uuid.UUID, scope: str) -> Optional[str]:
        res = await self.db.execute(
            select(AgentEphemeralCredential)
            .where(AgentEphemeralCredential.run_id == run_id)
            .where(AgentEphemeralCredential.scope == scope)
            .where(AgentEphemeralCredential.expires_at > utc_now())
            .order_by(AgentEphemeralCredential.created_at.desc())
        )
        cred = res.scalars().first()
        return cred.credential_value if cred else None

    async def revoke_run_credentials(self, run_id: uuid.UUID):
        from sqlalchemy import update
        await self.db.execute(
            update(AgentEphemeralCredential)
            .where(AgentEphemeralCredential.run_id == run_id)
            .values(expires_at=utc_now())
        )
        await self.db.commit()
