# Owner: agent-platform
import logging
import uuid
from datetime import timedelta

from app.core.time import utc_now
from app.models.core.connector_auth import ConnectorOAuthClient, ConnectorOAuthToken
from app.services.agents.connectors.connector_secret_store import connector_secret_store
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TokenRotationService:
    """
    Handles automatic rotation and refreshing of SaaS OAuth tokens.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def refresh_token_if_needed(self, token_id: uuid.UUID) -> str | None:
        stmt = select(ConnectorOAuthToken).where(ConnectorOAuthToken.id == token_id)
        res = await self.db.execute(stmt)
        token = res.scalar_one_or_none()

        if not token or token.status != "active":
            return None

        if token.expires_at and token.expires_at > utc_now() + timedelta(minutes=5):
            return connector_secret_store.decrypt(token.access_token_encrypted)

        if not token.refresh_token_encrypted:
            return None

        # Perform refresh
        logger.info(f"Refreshing OAuth token for {token_id}")

        stmt_c = select(ConnectorOAuthClient).where(ConnectorOAuthClient.id == token.client_id)
        res_c = await self.db.execute(stmt_c)
        client = res_c.scalar_one_or_none()

        if not client:
            return None

        refresh_token = connector_secret_store.decrypt(token.refresh_token_encrypted)

        # In a real app, this would make an HTTP call to client.token_url
        # For this prototype, we simulate a successful refresh
        new_access_token = f"refreshed_access_{uuid.uuid4()}"
        new_refresh_token = f"new_refresh_{uuid.uuid4()}"

        token.access_token_encrypted = connector_secret_store.encrypt(new_access_token)
        token.refresh_token_encrypted = connector_secret_store.encrypt(new_refresh_token)
        token.expires_at = utc_now() + timedelta(hours=1)
        token.updated_at = utc_now()

        await self.db.commit()

        return new_access_token

    async def revoke_token(self, token_id: uuid.UUID):
        stmt = select(ConnectorOAuthToken).where(ConnectorOAuthToken.id == token_id)
        res = await self.db.execute(stmt)
        token = res.scalar_one_or_none()
        if token:
            token.status = "revoked"
            await self.db.commit()
            logger.info(f"Revoked token {token_id}")
