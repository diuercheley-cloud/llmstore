from fastapi import FastAPI, HTTPException, Header, Depends
from services.agent_runtime.app.schemas.contract import AgentRunStartRequest, AgentRunResponse, AgentRunActionResponse
import uuid
import logging

app = FastAPI(title="Agent Runtime Service")
logger = logging.getLogger(__name__)

# Basic M2M Auth (Skeleton)
INTERNAL_TOKEN = "agent-runtime-secret-token"

async def verify_token(x_internal_token: str = Header(...)):
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid internal token")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

@app.post("/runs", response_model=AgentRunResponse, dependencies=[Depends(verify_token)])
async def start_run(request: AgentRunStartRequest):
    # This is a skeleton. Real implementation will be moved here later.
    logger.info(f"Starting run for agent {request.agent_id} in tenant {request.tenant_id}")
    return AgentRunResponse(
        id=uuid.uuid4(),
        agent_id=request.agent_id,
        tenant_id=request.tenant_id,
        status="queued",
        created_at="2026-06-11T21:20:00Z"
    )

@app.post("/runs/{run_id}/pause", response_model=AgentRunActionResponse, dependencies=[Depends(verify_token)])
async def pause_run(run_id: uuid.UUID):
    return AgentRunActionResponse(id=run_id, status="paused", message="Run paused successfully")

@app.post("/runs/{run_id}/resume", response_model=AgentRunActionResponse, dependencies=[Depends(verify_token)])
async def resume_run(run_id: uuid.UUID):
    return AgentRunActionResponse(id=run_id, status="running", message="Run resumed successfully")

@app.post("/runs/{run_id}/cancel", response_model=AgentRunActionResponse, dependencies=[Depends(verify_token)])
async def cancel_run(run_id: uuid.UUID):
    return AgentRunActionResponse(id=run_id, status="cancelled", message="Run cancelled successfully")
