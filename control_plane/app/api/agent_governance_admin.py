# Owner: agent-platform
import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session, require_admin
from app.models.agents import AgentPromotionGate
from app.services.agents.agent_policy_engine import AgentPolicyEngine
from app.services.agents.promotion_gate import AgentPromotionService
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/governance", tags=["agent-governance"])

@router.post("/{agent_id}/promotion-check")
async def promotion_check(
    agent_id: uuid.UUID,
    target_status: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentPromotionService(db)
    return await service.run_promotion_check(agent_id, target_status)

@router.post("/{agent_id}/promote")
async def promote_agent(
    agent_id: uuid.UUID,
    target_status: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentPromotionService(db)
    try:
        return await service.promote_agent(agent_id, target_status, approved_by=str(admin.get("id", "admin")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{agent_id}/promotion-history")
async def get_promotion_history(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    stmt = select(AgentPromotionGate).where(AgentPromotionGate.agent_id == agent_id).order_by(AgentPromotionGate.created_at.desc())
    res = await db.execute(stmt)
    gates = res.scalars().all()
    return [
        {
            "id": str(g.id),
            "target_status": g.target_status,
            "status": g.status,
            "eval_passed": g.eval_passed,
            "security_passed": g.security_passed,
            "created_at": g.created_at.isoformat()
        }
        for g in gates
    ]

@router.get("/policies")
async def list_global_policies(
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    # In a real scenario, these would be loaded from config/agent-policies/*.yaml
    return {
        "policies": [
            {"name": "max_steps_by_risk", "status": "active"},
            {"name": "allowed_tools_by_agent", "status": "active"},
            {"name": "no_shell_tool_by_default", "status": "active"},
            {"name": "approval_required_for_destructive_tools", "status": "active"},
            {"name": "no_production_agent_without_eval_baseline", "status": "active"},
        ]
    }

@router.post("/policies/simulate")
async def simulate_policy(
    agent_id: uuid.UUID = Body(...),
    action: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    engine = AgentPolicyEngine(db)
    return await engine.simulate_action(agent_id, action)

@router.get("/decisions")
async def list_recent_decisions(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    # Placeholder for recent policy engine logs
    return []
