from app.services.policy_engine.base import DecisionResult, PolicyContext
from app.services.policy_engine.orchestrator import PolicyEngineOrchestrator
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/admin/policies", tags=["admin-policies"])


@router.post("/evaluate")
async def evaluate_policy(
    context: PolicyContext,
    engine: str = Query("builtin", description="The engine to use for evaluation"),
    orchestrator: PolicyEngineOrchestrator = Depends(PolicyEngineOrchestrator),
):
    """
    Evaluates a policy context against the specified engine.
    """
    return await orchestrator.evaluate(context, engine)


@router.post("/dry-run")
async def policy_dry_run(
    context: PolicyContext,
    orchestrator: PolicyEngineOrchestrator = Depends(PolicyEngineOrchestrator),
):
    """
    Runs all configured engines and returns the comparison of decisions.
    """
    decisions = await orchestrator.evaluate_multi(context)

    # Simple reconciliation for dry-run
    # If any engine says deny, we mark as 'warning' in dry-run
    has_denial = any(d.result == DecisionResult.DENY for d in decisions)

    return {
        "context": context,
        "is_safe": not has_denial,
        "decisions": decisions,
        "reconciliation": "Most restrictive result would apply in production.",
    }


@router.get("/")
async def list_policies(orchestrator: PolicyEngineOrchestrator = Depends(PolicyEngineOrchestrator)):
    """
    Returns a list of available policy engines and their status.
    """
    return [{"name": e.get_engine_name(), "status": "active"} for e in orchestrator.engines]
