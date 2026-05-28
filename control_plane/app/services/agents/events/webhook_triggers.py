import hmac
import hashlib
import json
import logging
import uuid
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_events import AgentWebhookTrigger
from app.services.agents.events.event_triggers import fire_trigger
from app.core.config import get_settings

logger = logging.getLogger(__name__)

async def process_webhook(db: AsyncSession, trigger_id: uuid.UUID, payload: Dict[str, Any], signature: str) -> bool:
    """
    Verifies signature using AgentWebhookTrigger.secret_hash.
    Fires trigger if valid.
    """
    settings = get_settings()
    if not settings.agent_external_webhook_triggers_enabled:
        logger.warning("External webhook triggers are disabled by feature flag.")
        return False

    stmt = select(AgentWebhookTrigger).where(AgentWebhookTrigger.trigger_id == trigger_id)
    result = await db.execute(stmt)
    webhook_trigger = result.scalar_one_or_none()
    
    if not webhook_trigger:
        logger.error(f"Webhook trigger not found for trigger_id: {trigger_id}")
        return False

    # Verify signature
    # We assume payload is what was signed.
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    
    # We use webhook_trigger.secret_hash as the shared secret key
    expected_signature = hmac.new(
        webhook_trigger.secret_hash.encode("utf-8"), 
        body, 
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning(f"Invalid webhook signature for trigger_id: {trigger_id}")
        return False
        
    fired = await fire_trigger(db, trigger_id, payload)
    return fired
