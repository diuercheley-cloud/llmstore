# Owner: Platform Operations
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.models.core.connector_auth import ConnectorOAuthClient, ConnectorOAuthToken
from app.services.agents.connectors.connector_secret_store import connector_secret_store
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class OAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def register_client(self, tenant_id: str, connector_name: str, payload: Dict[str, Any]) -> ConnectorOAuthClient:
        client = ConnectorOAuthClient(
            tenant_id=tenant_id,
            connector_name=connector_name,
            client_id=payload["client_id"],
            client_secret_encrypted=connector_secret_store.encrypt(payload["client_secret"]),
            auth_url=payload["auth_url"],
            token_url=payload["token_url"],
            redirect_uri=payload["redirect_uri"]
        )
        self.db.add(client)
        await self.db.flush()
        return client

    async def start_flow(self, tenant_id: str, connector_name: str) -> Dict[str, Any]:
        if not self.settings.agent_connector_oauth_enabled:
            raise HTTPException(status_code=403, detail="OAuth flow is globally disabled.")

        stmt = select(ConnectorOAuthClient).where(
            ConnectorOAuthClient.tenant_id == tenant_id,
            ConnectorOAuthClient.connector_name == connector_name
        )
        res = await self.db.execute(stmt)
        client = res.scalar_one_or_none()
        
        if not client:
            raise HTTPException(status_code=404, detail=f"OAuth client not configured for {connector_name}")

        state = str(uuid.uuid4())
        # Store state in cache/redis in real app
        
        auth_url = f"{client.auth_url}?client_id={client.client_id}&redirect_uri={client.redirect_uri}&state={state}&response_type=code"
        return {"auth_url": auth_url, "state": state}

    async def handle_callback(self, tenant_id: str, connector_name: str, code: str, state: str):
        # Implementation of code-to-token exchange
        # (Mocked for prototype)
        
        stmt = select(ConnectorOAuthClient).where(
            ConnectorOAuthClient.tenant_id == tenant_id,
            ConnectorOAuthClient.connector_name == connector_name
        )
        res = await self.db.execute(stmt)
        client = res.scalar_one_or_none()
        
        token = ConnectorOAuthToken(
            client_id=client.id,
            tenant_id=tenant_id,
            access_token_encrypted=connector_secret_store.encrypt(f"access_{uuid.uuid4()}"),
            refresh_token_encrypted=connector_secret_store.encrypt(f"refresh_{uuid.uuid4()}"),
            scopes=["repo", "user"],
            status="active"
        )
        self.db.add(token)
        await self.db.commit()
        return {"status": "success", "token_id": str(token.id)}
