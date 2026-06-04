# Owner: agent-platform
from app.api import deps
from app.services.agents.environments.agent_environments import AgentEnvironmentsService
from app.services.agents.environments.promotion_workflow import PromotionWorkflowService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents", tags=["agent-environments-admin"])


class PromotePayload(BaseModel):
    from_environment: str
    to_environment: str
    version_id: str
    approve: bool = True  # Auto-approve if called by admin


@router.get("/{agent_id}/environments")
async def get_environments(
    agent_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Retrieves deployment version details across dev, staging, and production environments."""
    tenant_id = current_user.tenant_id
    data = await AgentEnvironmentsService.get_environments(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id
    )
    return data


@router.post("/{agent_id}/promote")
async def promote_agent(
    agent_id: str,
    payload: PromotePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Promotes an agent version to staging or production."""
    tenant_id = current_user.tenant_id
    username = getattr(current_user, "username", "admin")

    # 1. Create request
    req = await PromotionWorkflowService.create_promotion_request(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        from_env=payload.from_environment,
        to_env=payload.to_environment,
        version_id=payload.version_id,
        requested_by=username
    )

    # 2. If to production and approve is true, approve it
    if payload.to_environment.lower().strip() == "production" and payload.approve:
        approve_res = await PromotionWorkflowService.approve_promotion_request(
            db=db,
            tenant_id=tenant_id,
            request_id=str(req.id),
            approved_by=username
        )
        if approve_res["status"] == "error":
            raise HTTPException(status_code=400, detail=approve_res["message"])

    # 3. Execute
    res = await PromotionWorkflowService.execute_promotion(
        db=db,
        tenant_id=tenant_id,
        request_id=str(req.id)
    )

    if res["status"] == "policy_denied":
        raise HTTPException(status_code=400, detail=res["message"])
        
    if res["status"] == "error":
        raise HTTPException(status_code=500, detail=res["message"])

    return res


@router.post("/{agent_id}/rollback")
async def rollback_agent(
    agent_id: str,
    environment: str = Query(..., pattern="^(dev|staging|production)$"),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Rolls back the specified environment to the previous deployed version."""
    tenant_id = current_user.tenant_id
    res = await AgentEnvironmentsService.rollback_environment(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        environment=environment
    )

    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])

    return res
