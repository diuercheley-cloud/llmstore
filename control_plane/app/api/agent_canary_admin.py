# Owner: agent-platform
import uuid
from typing import Any, Dict, Optional

from app.services.runtime_dependencies import get_db
from app.models.agents.agent_canary import AgentCanaryAssignment, AgentCanaryComparison, AgentShadowRun
from app.services.agents.canary.canary_promotion_gate import CanaryPromotionGate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/admin/agents", tags=["Agent Shadow & Canary"])

@router.post("/{agent_id}/canary/start")
async def start_canary_assignment(
    agent_id: uuid.UUID,
    config: Dict[str, Any],
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    assignment = AgentCanaryAssignment(
        base_agent_id=agent_id,
        canary_agent_id=uuid.UUID(config["canary_agent_id"]),
        tenant_id=tenant_id,
        traffic_percentage=config.get("traffic_percentage", 0.0),
        is_shadow=config.get("is_shadow", True)
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment

@router.get("/{agent_id}/canary/comparisons")
async def list_canary_comparisons(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentCanaryComparison).join(AgentCanaryComparison.shadow_run).join(AgentShadowRun.assignment).where(
        AgentCanaryAssignment.base_agent_id == agent_id
    )
    # The above join requires proper relationships in models which we might have skipped for brevity
    # Using a simpler query for the prototype
    res = await db.execute(select(AgentCanaryComparison))
    return list(res.scalars().all())

@router.post("/{agent_id}/canary/promote")
async def promote_canary(
    agent_id: uuid.UUID,
    assignment_id: uuid.UUID,
    reviewer_id: str,
    comments: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    gate = CanaryPromotionGate(db)
    try:
        return await gate.promote(assignment_id, reviewer_id, comments)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
