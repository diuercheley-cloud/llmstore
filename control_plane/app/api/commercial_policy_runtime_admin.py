# Owner: commercial-ops
import uuid
from typing import Any

from app.models.commercial.commercial_policy_runtime import (
    CommercialPolicyEvaluation,
    CommercialPolicyViolation,
)
from app.services.auth import require_admin
from app.services.governance.policy_evaluator import PolicyEvaluator
from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(tags=["Policy Runtime Admin"], dependencies=[Depends(require_admin)])


@router.post("/admin/policy/runtime/evaluate")
def evaluate_policy(
    namespace: str,
    input_data: dict[str, Any],
    context: dict[str, Any],
    mode: str = "enforce",
    db: Session = Depends(get_db),
):
    """
    Evaluates a policy payload synchronously via the embedded Rego Runtime.
    """
    evaluator = PolicyEvaluator(db)
    result = evaluator.evaluate(namespace, input_data, context, mode=mode)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/admin/policy/runtime/simulate")
def simulate_policy(
    simulation_name: str,
    namespace: str,
    input_data: dict[str, Any],
    context: dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Runs a dry_run evaluation and records the result in simulations.
    """
    evaluator = PolicyEvaluator(db)
    result = evaluator.simulate(simulation_name, namespace, input_data, context)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/admin/policy/runtime/trace/{evaluation_id}")
def get_policy_trace(evaluation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves the explainability trace for a given evaluation.
    """
    evaluation = (
        db.query(CommercialPolicyEvaluation)
        .filter(CommercialPolicyEvaluation.id == evaluation_id)
        .first()
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"evaluation_id": evaluation.id, "trace": evaluation.decision_trace}


@router.get("/admin/policy/runtime/violations")
def list_violations(
    tenant_id: uuid.UUID = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Lists policy violations, optionally scoped by tenant.
    """
    query = db.query(CommercialPolicyViolation)
    if tenant_id:
        query = query.filter(CommercialPolicyViolation.tenant_id == tenant_id)
    violations = query.order_by(CommercialPolicyViolation.created_at.desc()).limit(limit).all()
    return violations


@router.get("/portal/policy/evaluations")
def list_portal_evaluations(
    tenant_id: uuid.UUID, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)
):
    """
    Portal endpoint for tenants to view their evaluation history.
    """
    evaluations = (
        db.query(CommercialPolicyEvaluation)
        .filter(CommercialPolicyEvaluation.tenant_id == tenant_id)
        .order_by(CommercialPolicyEvaluation.created_at.desc())
        .limit(limit)
        .all()
    )
    return evaluations
