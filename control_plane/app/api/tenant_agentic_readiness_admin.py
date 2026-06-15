# Owner: agent-platform
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.services.agents.tenant_agentic_readiness import TenantAgenticReadinessService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/tenants", tags=["tenant-agentic-readiness"])


@router.get("/{tenant_id}/agentic-readiness")
async def get_tenant_agentic_readiness(
    tenant_id: str, db: AsyncSession = Depends(get_db_session), admin: Any = Depends(require_admin)
) -> dict[str, Any]:
    """
    Returns the agentic readiness report for a specific tenant.
    Includes isolation checks, memory consent, and budget policies.
    """
    service = TenantAgenticReadinessService(db)
    report = await service.get_readiness_report(tenant_id)
    return report
