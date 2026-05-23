# Owner: agent-platform
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, get_db_session
from app.services.agents.tenant_agentic_readiness import TenantAgenticReadinessService

router = APIRouter(prefix="/admin/tenants", tags=["tenant-agentic-readiness"])

@router.get("/{tenant_id}/agentic-readiness")
async def get_tenant_agentic_readiness(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Returns the agentic readiness report for a specific tenant.
    Includes isolation checks, memory consent, and budget policies.
    """
    service = TenantAgenticReadinessService(db)
    report = await service.get_readiness_report(tenant_id)
    return report
