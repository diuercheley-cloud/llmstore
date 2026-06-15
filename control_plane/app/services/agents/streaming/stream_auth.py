# Owner: agent-platform
import logging
from datetime import UTC

from app.core.security import verify_secret
from app.core.time import utc_now
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from fastapi import HTTPException, WebSocket, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("stream_auth")


class StreamAuthService:
    @staticmethod
    async def authenticate_websocket(websocket: WebSocket, db: AsyncSession) -> Client:
        # Extract token or api_key from query params
        token = websocket.query_params.get("token") or websocket.query_params.get("api_key")
        if not token:
            logger.warning("WebSocket auth failed: missing credentials in query parameters.")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth credentials"
            )
            raise HTTPException(status_code=401, detail="Missing auth credentials")

        plaintext = token.strip()
        prefix = plaintext[:12]

        stmt = (
            select(ApiKey)
            .where(
                ApiKey.key_prefix == prefix, ApiKey.is_active == True, ApiKey.revoked_at.is_(None)
            )
            .order_by(ApiKey.created_at.desc())
        )

        result = await db.execute(stmt)
        api_keys = result.scalars().all()
        api_key = next((item for item in api_keys if verify_secret(plaintext, item.key_hash)), None)

        if not api_key:
            logger.warning(f"WebSocket auth failed: invalid api key with prefix {prefix}.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Check expiration
        if api_key.expires_at:
            expires_at = api_key.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < utc_now():
                logger.warning("WebSocket auth failed: API key has expired.")
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION, reason="API key expired"
                )
                raise HTTPException(status_code=401, detail="API key expired")

        # Fetch client
        client_res = await db.execute(select(Client).where(Client.id == api_key.client_id))
        client = client_res.scalar_one_or_none()

        if client is None or client.is_blocked:
            logger.warning(
                f"WebSocket auth failed: Client {api_key.client_id} not found or blocked."
            )
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Client blocked or not found"
            )
            raise HTTPException(status_code=403, detail="Client blocked or not found")

        if client.billing_status == "suspended":
            logger.warning(f"WebSocket auth failed: Client {client.id} is suspended.")
            await websocket.close(code=status.WS_1002_PROTOCOL_ERROR, reason="Billing suspended")
            raise HTTPException(status_code=402, detail="Billing suspended")

        return client
