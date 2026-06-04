# Owner: agent-platform
import uuid
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.models.agent_cicd import AgentDeployment, AgentPipeline, AgentRollback
from app.services.agents.cicd.agent_pipeline import AgentPipelineService
from app.services.agents.cicd.rollback_executor import RollbackExecutor
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/cicd", tags=["agent-cicd"])


class PipelineCreateRequest(BaseModel):
    agent_id: uuid.UUID
    tenant_id: str = Field(min_length=1, max_length=128)
    config: dict[str, Any] = Field(default_factory=dict)


class PipelineRunResponse(BaseModel):
    pipeline_id: str
    status: str


class RollbackRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _serialize_pipeline(pipeline: AgentPipeline) -> dict[str, Any]:
    return {
        "id": str(pipeline.id),
        "agent_id": str(pipeline.agent_id),
        "tenant_id": pipeline.tenant_id,
        "status": pipeline.status,
        "config": pipeline.config or {},
        "created_at": pipeline.created_at.isoformat(),
        "updated_at": pipeline.updated_at.isoformat(),
    }


def _serialize_deployment(deployment: AgentDeployment) -> dict[str, Any]:
    return {
        "id": str(deployment.id),
        "agent_id": str(deployment.agent_id),
        "pipeline_id": str(deployment.pipeline_id) if deployment.pipeline_id else None,
        "environment": deployment.environment,
        "strategy": deployment.strategy,
        "version_tag": deployment.version_tag,
        "status": deployment.status,
        "traffic_weight": deployment.traffic_weight,
        "created_at": deployment.created_at.isoformat(),
        "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
    }


def _serialize_rollback(rollback: AgentRollback) -> dict[str, Any]:
    return {
        "id": str(rollback.id),
        "deployment_id": str(rollback.deployment_id),
        "from_version": rollback.from_version,
        "to_version": rollback.to_version,
        "reason": rollback.reason,
        "status": rollback.status,
        "created_at": rollback.created_at.isoformat(),
    }


@router.post("/pipelines")
async def create_pipeline(
    payload: PipelineCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = AgentPipelineService(db)
    pipeline = await service.create_pipeline(payload.agent_id, payload.tenant_id, payload.config)
    await db.commit()
    await db.refresh(pipeline)
    return _serialize_pipeline(pipeline)


@router.post("/pipelines/{pipeline_id}/run", response_model=PipelineRunResponse)
async def run_pipeline(
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    stmt = select(AgentPipeline).where(AgentPipeline.id == pipeline_id)
    res = await db.execute(stmt)
    pipeline = res.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    service = AgentPipelineService(db)
    await service.run_pipeline(pipeline_id)
    await db.commit()
    await db.refresh(pipeline)
    return PipelineRunResponse(pipeline_id=str(pipeline.id), status=pipeline.status)


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    stmt = select(AgentPipeline).where(AgentPipeline.id == pipeline_id)
    res = await db.execute(stmt)
    pipeline = res.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    deployment_stmt = select(AgentDeployment).where(AgentDeployment.pipeline_id == pipeline_id)
    deployment_res = await db.execute(deployment_stmt)
    deployments = deployment_res.scalars().all()

    return {
        "pipeline": _serialize_pipeline(pipeline),
        "deployments": [_serialize_deployment(deployment) for deployment in deployments],
    }


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: uuid.UUID,
    payload: RollbackRequest,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    executor = RollbackExecutor(db)
    success = await executor.execute_rollback(deployment_id, payload.reason)
    await db.commit()
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")

    rollback_stmt = (
        select(AgentRollback)
        .where(AgentRollback.deployment_id == deployment_id)
        .order_by(AgentRollback.created_at.desc())
    )
    rollback_res = await db.execute(rollback_stmt)
    rollback = rollback_res.scalars().first()
    if not rollback:
        raise HTTPException(status_code=500, detail="Rollback record missing")
    return _serialize_rollback(rollback)
