# Owner: agent-platform
import logging
from typing import Any

from app.services.agents.provider_validation import (
    ALLOWED_PROVIDERS,
    get_latest_results,
    get_provider_matrix,
    is_recent_validation_available,
    run_validation_suite,
)
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/agents/provider-validation",
    tags=["admin-agent-provider-validation"],
    dependencies=[Depends(require_admin)],
)


@router.post("/run")
async def run_provider_validation(
    providers: str | None = Query(
        None, description="Comma-separated list of providers to validate"
    ),
    allow_paid: bool = Query(False, description="Allow paid provider calls"),
    budget_brl: float = Query(1.00, description="Maximum budget in BRL", ge=0.01, le=10.00),
    timeout_seconds: int = Query(60, description="Per-request timeout in seconds", ge=1, le=300),
) -> dict[str, Any]:
    import os

    # Set env overrides for this request
    os.environ["AGENT_REAL_PROVIDER_VALIDATION_ENABLED"] = "true"
    os.environ["AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID"] = "true" if allow_paid else "false"
    os.environ["AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL"] = str(budget_brl)
    os.environ["AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS"] = str(timeout_seconds)

    provider_list = [p.strip() for p in providers.split(",")] if providers else None

    if provider_list:
        invalid = [p for p in provider_list if p not in ALLOWED_PROVIDERS]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid providers: {invalid}. Allowed: {ALLOWED_PROVIDERS}",
            )

    logger.info(
        "Admin triggered provider validation: providers=%s allow_paid=%s budget=%.2f timeout=%d",
        provider_list or "all",
        allow_paid,
        budget_brl,
        timeout_seconds,
    )

    try:
        result = await run_validation_suite(provider_list)
        return result
    except Exception as e:
        logger.exception("Provider validation run failed")
        raise HTTPException(status_code=500, detail=f"Validation run failed: {str(e)}")


@router.get("/latest")
async def get_latest_validation_results() -> dict[str, Any]:
    result = await get_latest_results()
    if result.get("status") == "not_generated":
        raise HTTPException(
            status_code=404,
            detail="No validation results found. Run POST /admin/agents/provider-validation/run first.",
        )
    return result


@router.get("/providers")
async def list_available_providers() -> list[dict[str, Any]]:
    return get_provider_matrix()


@router.get("/check")
async def check_validation_recency() -> dict[str, Any]:
    recent = is_recent_validation_available(max_age_hours=24)
    return {
        "recent_validation_available": recent,
        "max_age_hours": 24,
    }
