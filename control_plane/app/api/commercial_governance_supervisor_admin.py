# Owner: commercial-ops
from typing import Any, Dict, List

from app.api.dependencies import get_current_admin, get_db
from app.models.commercial.commercial_governance_supervisor import (
    CommercialGovernanceSupervisorAction,
    CommercialGovernanceSupervisorDecision,
    CommercialGovernanceSupervisorIncident,
    CommercialGovernanceSupervisorRiskScore,
)
from app.services.governance.governance_supervisor import GovernanceSupervisor
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/status", response_model=Dict[str, Any])
async def get_supervisor_status(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    """
    Get the overall health and status of the autonomous governance supervisor.
    """
    # Trigger a manual cycle for testing/admin purposes
    supervisor = GovernanceSupervisor(db)
    result = await supervisor.run_supervisor_cycle()
    return {"supervisor_status": "active", "last_cycle": result}

@router.get("/incidents", response_model=List[Dict[str, Any]])
async def get_supervisor_incidents(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    result = await db.execute(select(CommercialGovernanceSupervisorIncident).limit(100))
    incidents = result.scalars().all()
    return [{"id": str(i.id), "type": i.incident_type, "severity": i.severity, "status": i.status} for i in incidents]

@router.get("/decisions", response_model=List[Dict[str, Any]])
async def get_supervisor_decisions(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    result = await db.execute(select(CommercialGovernanceSupervisorDecision).limit(100))
    decisions = result.scalars().all()
    return [{"id": str(d.id), "type": d.decision_type, "mode": d.mode_used, "approved": d.is_approved} for d in decisions]

@router.get("/risk", response_model=List[Dict[str, Any]])
async def get_supervisor_risk(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    result = await db.execute(select(CommercialGovernanceSupervisorRiskScore).order_by(CommercialGovernanceSupervisorRiskScore.calculated_at.desc()).limit(10))
    scores = result.scalars().all()
    return [{"id": str(s.id), "overall": s.overall_risk_score, "financial": s.financial_risk, "compliance": s.compliance_risk} for s in scores]

@router.get("/actions", response_model=List[Dict[str, Any]])
async def get_supervisor_actions(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    result = await db.execute(select(CommercialGovernanceSupervisorAction).limit(100))
    actions = result.scalars().all()
    return [{"id": str(a.id), "type": a.action_type, "status": a.status} for a in actions]

@router.get("/explainability/{decision_id}", response_model=Dict[str, Any])
async def get_supervisor_explainability(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    """
    Returns the explainability report for a specific decision.
    In a full implementation, this fetches the report from blob storage or a structured DB table.
    """
    decision = await db.get(CommercialGovernanceSupervisorDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
        
    return {
        "decision_id": str(decision.id),
        "rationale": decision.rationale,
        "mode_used": decision.mode_used,
        "expected_impact": decision.expected_impact
    }
