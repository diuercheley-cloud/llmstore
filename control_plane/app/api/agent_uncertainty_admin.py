# Owner: agent-platform
import uuid
from typing import Any, Dict

from app.db.session import get_db
from app.models.agent_uncertainty import AgentUncertaintyEvent, AgentUncertaintyPolicy
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/admin/agents", tags=["Agent Epistemic Uncertainty"])

@router.get("/{agent_id}/uncertainty-events")
async def list_uncertainty_events(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentUncertaintyEvent).where(AgentUncertaintyEvent.agent_id == agent_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())

@router.post("/{agent_id}/uncertainty-policy")
async def update_uncertainty_policy(
    agent_id: uuid.UUID,
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentUncertaintyPolicy).where(AgentUncertaintyPolicy.agent_id == agent_id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    
    if not policy:
        policy = AgentUncertaintyPolicy(agent_id=agent_id)
        db.add(policy)
        
    policy.min_confidence_threshold = config.get("min_confidence_threshold", policy.min_confidence_threshold)
    policy.auto_research_enabled = config.get("auto_research_enabled", policy.auto_research_enabled)
    policy.hitl_on_low_confidence = config.get("hitl_on_low_confidence", policy.hitl_on_low_confidence)
    
    await db.commit()
    await db.refresh(policy)
    return policy
