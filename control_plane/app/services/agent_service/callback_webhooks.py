# Owner: agent-platform
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import requests
from app.models.agents.agent_service import AgentCallbackWebhook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CallbackWebhookService:
    """
    Manages and executes callback webhooks for agent completion.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_webhook(
        self, agent_id: uuid.UUID, tenant_id: str, url: str
    ) -> AgentCallbackWebhook:
        secret = uuid.uuid4().hex
        webhook = AgentCallbackWebhook(
            agent_id=agent_id, tenant_id=tenant_id, url=url, secret_key=secret, is_active=True
        )
        self.db.add(webhook)
        await self.db.flush()
        return webhook

    async def trigger_callback(self, agent_id: uuid.UUID, payload: dict[str, Any]):
        """
        Sends the payload to all active webhooks for the agent.
        """
        stmt = select(AgentCallbackWebhook).where(
            AgentCallbackWebhook.agent_id == agent_id, AgentCallbackWebhook.is_active == True
        )
        res = await self.db.execute(stmt)
        webhooks = res.scalars().all()

        for wh in webhooks:
            await self._send_signed_request(wh.url, wh.secret_key, payload)

    async def _send_signed_request(self, url: str, secret: str, payload: dict[str, Any]):
        body = json.dumps(payload)
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

        headers = {"Content-Type": "application/json", "X-Agent-Signature": signature}

        try:
            # In production, use an async HTTP client and a background task runner
            requests.post(url, data=body, headers=headers, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
