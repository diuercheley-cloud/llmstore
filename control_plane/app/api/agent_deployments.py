# Owner: agent-platform
"""
Agent-as-API Deployment Endpoints

Admin endpoints (require_admin):
  POST /admin/agents/{id}/deployments        - Create deployment
  GET  /admin/agents/deployments              - List deployments
  GET  /admin/agents/deployments/{id}         - Get deployment
  PATCH /admin/agents/deployments/{id}        - Update deployment
  POST /admin/agents/deployments/{id}/pause   - Pause
  POST /admin/agents/deployments/{id}/resume  - Resume
  POST /admin/agents/deployments/{id}/archive - Archive
  POST /admin/agents/deployments/{id}/rollback - Rollback
  POST /admin/agents/deployments/{id}/keys    - Create API key
  GET  /admin/agents/deployments/{id}/usage   - Usage stats
  GET  /admin/agents/deployments/{id}/sla     - SLA summary

Public endpoints (endpoint key auth):
  POST /api/agents/{slug}/invoke              - Async invoke
  POST /api/agents/{slug}/invoke-sync         - Sync invoke
  GET  /api/agents/{slug}/runs/{run_id}       - Get run status
"""
import logging
import time
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.agent_deployments.agent_api_deployment import (
    AgentApiDeploymentService,
    DeploymentNotFoundError,
    DeploymentValidationError,
)
from app.services.agent_deployments.agent_endpoint_registry import AgentEndpointRegistry
from app.services.agent_deployments.deployment_sla import DeploymentSlaService
from app.services.agent_deployments.deployment_usage import DeploymentUsageService
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Admin Router ──────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/agents",
    tags=["agent-deployments-admin"],
    dependencies=[Depends(require_admin)],
)


class DeploymentCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    timeout_seconds: int = 30
    max_concurrency: int = 10
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000
    retry_max_attempts: int = 0
    callback_url: Optional[str] = None
    billing_tier: str = "free"


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    timeout_seconds: Optional[int] = None
    max_concurrency: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    retry_max_attempts: Optional[int] = None
    retry_backoff_ms: Optional[int] = None
    callback_url: Optional[str] = None
    billing_tier: Optional[str] = None


class RollbackRequest(BaseModel):
    target_version_slug: str


def _check_enabled():
    if not settings.agent_as_api_enabled:
        raise HTTPException(status_code=403, detail="Agent-as-API is disabled")


def _serialize_deployment(d) -> Dict[str, Any]:
    return {
        "id": str(d.id),
        "tenant_id": d.tenant_id,
        "agent_id": str(d.agent_id),
        "slug": d.slug,
        "name": d.name,
        "description": d.description,
        "status": d.status,
        "version": d.version,
        "previous_version_slug": d.previous_version_slug,
        "timeout_seconds": d.timeout_seconds,
        "max_concurrency": d.max_concurrency,
        "retry_max_attempts": d.retry_max_attempts,
        "retry_backoff_ms": d.retry_backoff_ms,
        "rate_limit_per_minute": d.rate_limit_per_minute,
        "rate_limit_per_day": d.rate_limit_per_day,
        "callback_url": d.callback_url,
        "billing_tier": d.billing_tier,
        "cost_per_invocation_brl": d.cost_per_invocation_brl,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
        "archived_at": d.archived_at.isoformat() if d.archived_at else None,
    }


@admin_router.post("/{agent_id}/deployments")
async def create_deployment(
    agent_id: uuid.UUID,
    payload: DeploymentCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Deploy an active/approved agent as a dedicated API endpoint."""
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.create_deployment(
            tenant_id="admin",  # Admin-managed, tenant from agent
            agent_id=agent_id,
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            timeout_seconds=payload.timeout_seconds,
            max_concurrency=payload.max_concurrency,
            rate_limit_per_minute=payload.rate_limit_per_minute,
            rate_limit_per_day=payload.rate_limit_per_day,
            retry_max_attempts=payload.retry_max_attempts,
            callback_url=payload.callback_url,
            billing_tier=payload.billing_tier,
        )
        await session.commit()

        # Get the default key
        from app.models.agent_deployments import AgentApiEndpointKey
        from sqlalchemy import select
        stmt = select(AgentApiEndpointKey).where(
            AgentApiEndpointKey.deployment_id == deployment.id
        )
        res = await session.execute(stmt)
        key = res.scalar_one_or_none()

        result = _serialize_deployment(deployment)
        if key:
            result["endpoint_key_prefix"] = key.key_prefix
        return result
    except DeploymentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.get("/deployments")
async def list_deployments(
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_db_session),
):
    """List all deployments."""
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    deployments = await svc.list_deployments("admin", include_archived)
    return [_serialize_deployment(d) for d in deployments]


@admin_router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get deployment details."""
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    deployment = await svc.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _serialize_deployment(deployment)


@admin_router.patch("/deployments/{deployment_id}")
async def update_deployment(
    deployment_id: uuid.UUID,
    payload: DeploymentUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update deployment configuration."""
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.update_deployment(
            deployment_id, "admin", **payload.model_dump(exclude_none=True)
        )
        await session.commit()
        return _serialize_deployment(deployment)
    except DeploymentNotFoundError:
        raise HTTPException(status_code=404, detail="Deployment not found")


@admin_router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.pause_deployment(deployment_id, "admin")
        await session.commit()
        return _serialize_deployment(deployment)
    except DeploymentNotFoundError:
        raise HTTPException(status_code=404, detail="Deployment not found")


@admin_router.post("/deployments/{deployment_id}/resume")
async def resume_deployment(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.resume_deployment(deployment_id, "admin")
        await session.commit()
        return _serialize_deployment(deployment)
    except DeploymentNotFoundError:
        raise HTTPException(status_code=404, detail="Deployment not found")


@admin_router.post("/deployments/{deployment_id}/promote")
async def promote_deployment(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.promote_deployment(deployment_id, "admin")
        await session.commit()
        return _serialize_deployment(deployment)
    except DeploymentNotFoundError:
        raise HTTPException(status_code=404, detail="Deployment not found")


@admin_router.post("/deployments/{deployment_id}/archive")
async def archive_deployment(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.archive_deployment(deployment_id, "admin")
        await session.commit()
        return _serialize_deployment(deployment)
    except DeploymentNotFoundError:
        raise HTTPException(status_code=404, detail="Deployment not found")


@admin_router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: uuid.UUID,
    payload: RollbackRequest,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    try:
        deployment = await svc.rollback_deployment(
            deployment_id, "admin", payload.target_version_slug
        )
        await session.commit()
        return _serialize_deployment(deployment)
    except (DeploymentNotFoundError, DeploymentValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.post("/deployments/{deployment_id}/keys")
async def create_endpoint_key(
    deployment_id: uuid.UUID,
    name: str = Query("default"),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new API key for a deployment."""
    _check_enabled()
    svc = AgentApiDeploymentService(session)
    deployment = await svc.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    key, raw_key = await svc.create_endpoint_key(deployment_id, "admin", name)
    await session.commit()
    return {
        "id": str(key.id),
        "name": key.name,
        "key": raw_key,
        "key_prefix": key.key_prefix,
        "warning": "Store this key securely - it will not be shown again",
    }


@admin_router.get("/deployments/{deployment_id}/usage")
async def get_usage_stats(
    deployment_id: uuid.UUID,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = DeploymentUsageService(session)
    return await svc.get_usage_stats(deployment_id, days)


@admin_router.get("/deployments/{deployment_id}/sla")
async def get_sla_summary(
    deployment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = DeploymentSlaService(session)
    return await svc.get_sla_summary(deployment_id)


# ── Public Router (endpoint-key authenticated) ────────────────────

public_router = APIRouter(
    prefix="/api/agents",
    tags=["agent-deployments"],
)


class InvokeRequest(BaseModel):
    input: str
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InvokeSyncRequest(BaseModel):
    input: str
    timeout: Optional[int] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


async def _authenticate_deployment(request: Request, slug: str):
    """Authenticate via deployment endpoint key."""
    _check_enabled()
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    raw_key = auth_header[7:]

    svc = AgentApiDeploymentService(request.state._db if hasattr(request.state, '_db') else None)
    # We need the db session - use the request's state or create one
    from app.db.session import SessionLocal
    async with SessionLocal() as db:
        svc = AgentApiDeploymentService(db)
        result = await svc.validate_endpoint_key(raw_key, slug)
        if not result:
            raise HTTPException(status_code=403, detail="Invalid or expired endpoint key")
        deployment, key = result
        return deployment, key


@public_router.post("/{slug}/invoke")
async def invoke_agent(
    slug: str,
    payload: InvokeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Invoke agent asynchronously. Returns run_id for polling."""
    _check_enabled()

    # Auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    raw_key = auth_header[7:]

    svc = AgentApiDeploymentService(session)
    result = await svc.validate_endpoint_key(raw_key, slug)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid or expired endpoint key")
    deployment, key = result

    # Invoke
    registry = AgentEndpointRegistry(session)
    response = await registry.invoke_async(
        deployment=deployment,
        input_text=payload.input,
        tenant_id=str(deployment.tenant_id),
        client_ip=request.client.host if request.client else None,
        endpoint_key_id=key.id,
    )

    # Record usage
    usage_svc = DeploymentUsageService(session)
    run_id = response.get("run_id")
    await usage_svc.record_invocation(
        deployment=deployment,
        run_id=uuid.UUID(run_id) if run_id else None,
        endpoint_key_id=key.id,
        mode="async",
        status="started" if run_id else "failed",
        input_text=payload.input,
        error_message=response.get("error"),
        client_ip=request.client.host if request.client else None,
    )
    await session.commit()

    if "error" in response:
        raise HTTPException(status_code=429 if "limit" in response["error"].lower() else 500, detail=response["error"])
    return response


@public_router.post("/{slug}/invoke-sync")
async def invoke_agent_sync(
    slug: str,
    payload: InvokeSyncRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Invoke agent synchronously. Blocks until complete or timeout."""
    _check_enabled()

    # Auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    raw_key = auth_header[7:]

    svc = AgentApiDeploymentService(session)
    result = await svc.validate_endpoint_key(raw_key, slug)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid or expired endpoint key")
    deployment, key = result

    # Invoke sync
    start_time = time.time()
    registry = AgentEndpointRegistry(session)
    response = await registry.invoke_sync(
        deployment=deployment,
        input_text=payload.input,
        tenant_id=str(deployment.tenant_id),
        timeout_seconds=payload.timeout,
        client_ip=request.client.host if request.client else None,
        endpoint_key_id=key.id,
    )
    latency_ms = int((time.time() - start_time) * 1000)

    # Record usage
    usage_svc = DeploymentUsageService(session)
    run_id = response.get("run_id")
    status = "completed" if response.get("status") == "completed" else "timeout" if "timeout" in str(response.get("error", "")).lower() else "failed"
    await usage_svc.record_invocation(
        deployment=deployment,
        run_id=uuid.UUID(run_id) if run_id else None,
        endpoint_key_id=key.id,
        mode="sync",
        status=status,
        input_text=payload.input,
        latency_ms=latency_ms,
        tokens_used=response.get("total_tokens", 0),
        cost_brl=response.get("estimated_cost_brl", 0.0),
        error_message=response.get("error"),
        client_ip=request.client.host if request.client else None,
    )
    await session.commit()

    if "error" in response:
        status_code = 429 if "limit" in response["error"].lower() else 504 if "timeout" in response["error"].lower() else 500
        raise HTTPException(status_code=status_code, detail=response["error"])
    return response


@public_router.get("/{slug}/runs/{run_id}")
async def get_deployment_run(
    slug: str,
    run_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Get run status for a deployment invocation."""
    _check_enabled()

    # Auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    raw_key = auth_header[7:]

    svc = AgentApiDeploymentService(session)
    result = await svc.validate_endpoint_key(raw_key, slug)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid or expired endpoint key")
    deployment, key = result

    from app.services.agents import agent_state
    run = await agent_state.get_agent_run(session, run_id)
    if not run or str(run.agent_id) != str(deployment.agent_id):
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": str(run.id),
        "deployment_slug": slug,
        "status": run.status,
        "total_steps": run.total_steps,
        "total_tokens": run.total_tokens,
        "estimated_cost_brl": run.estimated_cost_brl,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "failure_reason": run.failure_reason,
    }
