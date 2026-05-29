# Owner: platform-ops
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import require_admin, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.agent_readiness import AgentReadinessService

router = APIRouter(prefix="/admin/readiness", tags=["readiness"])

@router.get("/{capability}")
async def get_capability_readiness(
    capability: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Check readiness for a specific capability.
    """
    # Mapping capability IDs to service check names if different
    service = AgentReadinessService(db)
    readiness = await service.check_readiness()
    
    # Filter or augment results based on capability
    # In a real implementation, we would have specific logic per capability.
    # For now, we reuse the AgentReadinessService which scans critical services.
    
    # Simulate capability specific check
    if capability == "agent-runtime" and not readiness.get("services", {}).get("agent_runtime", {}).get("ready"):
        raise HTTPException(status_code=503, detail="Agent Runtime not ready")
        
    return {
        "capability": capability,
        "status": readiness.get("status", "UNKNOWN"),
        "details": readiness
    }
