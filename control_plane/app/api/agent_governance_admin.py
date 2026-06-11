# Owner: agent-platform
import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session, require_admin
from app.models.agents.agents import AgentPromotionGate
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

@router.get("/dlp/violations")
async def list_dlp_violations(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    from app.models.agents.dlp import AgentDLPViolation
    stmt = select(AgentDLPViolation)
    if tenant_id:
        stmt = stmt.where(AgentDLPViolation.tenant_id == tenant_id)
    stmt = stmt.order_by(AgentDLPViolation.created_at.desc())
    
    res = await db.execute(stmt)
    violations = res.scalars().all()
    return [
        {
            "id": str(v.id),
            "run_id": str(v.run_id) if v.run_id else None,
            "tenant_id": v.tenant_id,
            "direction": v.direction,
            "content_type": v.content_type,
            "findings": v.findings,
            "action_taken": v.action_taken,
            "created_at": v.created_at.isoformat()
        }
        for v in violations
    ]

@router.get("/dlp/stats")
async def get_dlp_stats(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    from app.models.agents.dlp import AgentDLPViolation
    stmt = select(AgentDLPViolation)
    if tenant_id:
        stmt = stmt.where(AgentDLPViolation.tenant_id == tenant_id)
        
    res = await db.execute(stmt)
    violations = res.scalars().all()
    
    total = len(violations)
    by_category = {}
    by_direction = {"ingress": 0, "egress": 0}
    by_action = {}
    
    for v in violations:
        by_direction[v.direction] = by_direction.get(v.direction, 0) + 1
        by_action[v.action_taken] = by_action.get(v.action_taken, 0) + 1
        
        findings = v.findings or []
        for f in findings:
            cat = f.get("type", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            
    return {
        "total_violations": total,
        "by_category": by_category,
        "by_direction": by_direction,
        "by_action": by_action
    }
