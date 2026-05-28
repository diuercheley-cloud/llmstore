# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from app.services.agents.workflows.workflow_webhooks import WorkflowWebhookService
from app.services.agents.workflows.workflow_polling import WorkflowPollingService
from app.models.agent_workflows import AgentWorkflow, AgentWorkflowRun
from app.models.agent_workflows_external import AgentWorkflowExternalEvent

router = APIRouter(prefix="/admin/agents/workflows", tags=["agent-workflows-admin"])

# External Schemas
class PollingJobCreate(BaseModel):
    url: str
    stop_condition: Dict[str, Any]
    interval: int = 60

class WebhookResponse(BaseModel):
    id: uuid.UUID
    secret_token: str
    webhook_url: str

# Existing Schemas
class WorkflowCreate(BaseModel):
    name: str
    version: str
    tenant_id: str
    input_data: Dict[str, Any] = Field(default_factory=dict)

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    tenant_id: str
    status: str

class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    current_state: str
    context: Dict[str, Any]

class SignalRequest(BaseModel):
    signal_name: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRequest(BaseModel):
    tenant_id: str = "default"
    input_data: Dict[str, Any] = Field(default_factory=dict)

# Endpoints
@router.post("", response_model=WorkflowResponse)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db_session)):
    workflow = AgentWorkflow(
        name=payload.name,
        version=payload.version,
        tenant_id=payload.tenant_id,
        input_data=payload.input_data
    )
    db.add(workflow)
    await db.commit()
    return workflow

@router.post("/{id}/run", response_model=WorkflowRunResponse)
async def run_workflow(id: uuid.UUID, payload: WorkflowRunRequest, db: AsyncSession = Depends(get_db_session)):
    engine = WorkflowEngine(db)
    run = await engine.create_run(id, payload.tenant_id, payload.input_data)
    return run

@router.get("/{id}/run/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(id: uuid.UUID, run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select
    res = await db.execute(select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run

@router.post("/{id}/run/{run_id}/signal")
async def signal_workflow(id: uuid.UUID, run_id: uuid.UUID, payload: SignalRequest, db: AsyncSession = Depends(get_db_session)):
    engine = WorkflowEngine(db)
    await engine.signal_run(run_id, payload.signal_name, payload.payload)
    return {"status": "signal_sent"}

@router.post("/{id}/run/{run_id}/cancel")
async def cancel_workflow(id: uuid.UUID, run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    engine = WorkflowEngine(db)
    await engine.cancel_run(run_id)
    return {"status": "cancelled"}

@router.post("/{id}/run/{run_id}/webhook-wait", response_model=WebhookResponse)
async def create_webhook_wait(id: uuid.UUID, run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    service = WorkflowWebhookService(db)
    sub = await service.create_subscription(run_id, "default")
    await db.commit()
    return WebhookResponse(
        id=sub.id,
        secret_token=sub.secret_token,
        webhook_url=f"/agents/workflows/webhooks/{sub.id}"
    )

@router.post("/{id}/run/{run_id}/polling-job")
async def create_polling_job(id: uuid.UUID, run_id: uuid.UUID, payload: PollingJobCreate, db: AsyncSession = Depends(get_db_session)):
    service = WorkflowPollingService(db)
    job = await service.create_polling_job(run_id, "default", payload.url, payload.stop_condition, payload.interval)
    await db.commit()
    return {"status": "polling_started", "job_id": job.id}

@router.get("/{id}/run/{run_id}/external-events")
async def get_external_events(id: uuid.UUID, run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select
    stmt = select(AgentWorkflowExternalEvent).where(AgentWorkflowExternalEvent.run_id == run_id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/webhooks/{subscription_id}")
async def handle_workflow_webhook(subscription_id: uuid.UUID, payload: Dict[str, Any], secret_token: str, db: AsyncSession = Depends(get_db_session)):
    service = WorkflowWebhookService(db)
    return await service.handle_incoming(subscription_id, payload, secret_token)
