# Owner: platform-ops
"""Admin test-only endpoints for routing validation.

Protected by admin token and only active when REAL_PROVIDER_VALIDATION_ENABLED=true.
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.auth import require_admin

router = APIRouter(
    prefix="/admin/routing/test",
    tags=["admin", "routing", "test"],
    dependencies=[Depends(require_admin)],
)


class ForceLocalFailureRequest(BaseModel):
    enabled: bool


class ForceLocalFailureResponse(BaseModel):
    routing_test_force_local_failure: bool
    message: str


def _check_validation_mode():
    settings = get_settings()
    if not settings.real_provider_validation_enabled:
        raise HTTPException(
            status_code=403,
            detail="Test endpoint only available when REAL_PROVIDER_VALIDATION_ENABLED=true",
        )


@router.get("/force-local-failure", response_model=ForceLocalFailureResponse)
async def get_force_local_failure():
    _check_validation_mode()
    settings = get_settings()
    return ForceLocalFailureResponse(
        routing_test_force_local_failure=settings.routing_test_force_local_failure,
        message="Current force-local-failure status",
    )


@router.post("/force-local-failure", response_model=ForceLocalFailureResponse)
async def set_force_local_failure(payload: ForceLocalFailureRequest):
    _check_validation_mode()
    val = "true" if payload.enabled else "false"
    os.environ["ROUTING_TEST_FORCE_LOCAL_FAILURE"] = val
    from app.core.config import get_settings
    get_settings.cache_clear()
    return ForceLocalFailureResponse(
        routing_test_force_local_failure=payload.enabled,
        message=f"Local failure {'enabled' if payload.enabled else 'disabled'}. Set ROUTING_TEST_FORCE_LOCAL_FAILURE={val}",
    )
