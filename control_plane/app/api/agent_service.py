# Owner: agent-platform
import uuid

from app.api import deps
from app.services.agent_service.agent_service_api import AgentServiceAPI
from app.services.agent_service.callback_webhooks import CallbackWebhookService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agent-service", tags=["agent-as-a-service"])

@router.post("/{agent_id}/invoke")
async def invoke_agent(
    agent_id: uuid.UUID,
    input_text: str,
    tier: str = Query("free"),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    api = AgentServiceAPI(db)
    return await api.invoke_agent(agent_id, current_user.tenant_id, input_text, mode="async", tier_name=tier)

@router.post("/{agent_id}/invoke-sync")
async def invoke_agent_sync(
    agent_id: uuid.UUID,
    input_text: str,
    timeout: int = 30,
    tier: str = Query("pro"), # Usually sync is a paid feature
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    api = AgentServiceAPI(db)
    return await api.invoke_agent(agent_id, current_user.tenant_id, input_text, mode="sync", tier_name=tier)

@router.post("/{agent_id}/callbacks")
async def register_callback(
    agent_id: uuid.UUID,
    url: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    service = CallbackWebhookService(db)
    webhook = await service.register_webhook(agent_id, current_user.tenant_id, url)
    await db.commit()
    return {"status": "registered", "webhook_id": str(webhook.id), "secret": webhook.secret_key}

@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    from app.services.agents import agent_state
    run = await agent_state.get_agent_run(db, run_id)
    if not run or run.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Run not found")
        
    return {
        "run_id": str(run.id),
        "status": run.status,
        "total_steps": run.total_steps,
        "completed_at": run.completed_at
    }
