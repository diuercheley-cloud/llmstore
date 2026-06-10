# Owner: Platform Operations
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agents.agent_workflows_external import (
    AgentWorkflowExternalEvent,
    AgentWorkflowWebhookSubscription,
)
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class WorkflowWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.signals = WorkflowSignalManager(db)
        self.settings = get_settings()

    async def create_subscription(self, run_id: uuid.UUID, tenant_id: str) -> AgentWorkflowWebhookSubscription:
        if not self.settings.agent_workflow_webhooks_enabled:
            raise HTTPException(status_code=403, detail="Workflow webhooks are disabled.")

        sub = AgentWorkflowWebhookSubscription(
            run_id=run_id,
            tenant_id=tenant_id,
            secret_token=str(uuid.uuid4()),
            status="active"
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def handle_incoming(self, subscription_id: uuid.UUID, payload: Dict[str, Any], secret_token: str):
        stmt = select(AgentWorkflowWebhookSubscription).where(
            AgentWorkflowWebhookSubscription.id == subscription_id
        )
        res = await self.db.execute(stmt)
        sub = res.scalar_one_or_none()
        
        if not sub or sub.status != "active":
            raise HTTPException(status_code=404, detail="Webhook subscription not found or inactive")
            
        if sub.secret_token != secret_token:
            raise HTTPException(status_code=401, detail="Invalid webhook secret token")

        # 1. Record event
        event = AgentWorkflowExternalEvent(
            run_id=sub.run_id,
            tenant_id=sub.tenant_id,
            event_source="webhook",
            payload=payload,
            sanitized_payload=self._sanitize(payload)
        )
        self.db.add(event)
        
        # 2. Update status
        sub.status = "triggered"
        
        # 3. Send signal to wake up workflow
        await self.signals.send_signal(
            run_id=sub.run_id,
            signal_name=f"webhook_received_{subscription_id}",
            payload=payload
        )
        
        await self.db.commit()
        return {"status": "success", "event_id": str(event.id)}

    def _sanitize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Simple redaction of common sensitive keys
        sensitive = {"token", "secret", "password", "key", "auth"}
        return {k: ("[REDACTED]" if k.lower() in sensitive else v) for k, v in payload.items()}
