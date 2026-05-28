import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.services.agents.events.webhook_triggers import process_webhook
from app.core.config import get_settings
from app.models.agent_events import AgentWebhookTrigger

router = APIRouter(prefix="/agents/events", tags=["agent-events-public"])

@router.post("/webhooks/{trigger_id}")
async def handle_agent_webhook(
    trigger_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    if not settings.agent_event_driven_enabled or not settings.agent_external_webhook_triggers_enabled:
        raise HTTPException(status_code=403, detail="Webhook triggers are disabled by feature flag.")
        
    stmt = select(AgentWebhookTrigger).where(AgentWebhookTrigger.trigger_id == trigger_id)
    result = await db.execute(stmt)
    webhook_trigger = result.scalar_one_or_none()
    
    if not webhook_trigger:
        raise HTTPException(status_code=404, detail="Webhook trigger not found")
        
    sig_header = webhook_trigger.signature_header or "X-Agent-Signature"
    signature = request.headers.get(sig_header)
    if not signature:
        raise HTTPException(status_code=401, detail=f"Missing signature header {sig_header}")
        
    payload = await request.json()
    
    # process_webhook will check signature validation
    success = await process_webhook(db, trigger_id, payload, signature)
    
    if not success:
        raise HTTPException(status_code=403, detail="Invalid signature verification")
        
    return {"status": "accepted"}
