# Owner: agent-platform
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.services.agents.agent_readiness import AgentReadinessService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/readiness", tags=["agent-readiness"])


@router.get("")
async def get_agent_readiness(
    db: AsyncSession = Depends(get_db_session), admin: Any = Depends(require_admin)
) -> dict[str, Any]:
    """
    Returns the current readiness status of the agentic runtime.
    """
    service = AgentReadinessService(db)
    return await service.check_readiness()


@router.post("/run")
async def run_readiness_check(
    db: AsyncSession = Depends(get_db_session), admin: Any = Depends(require_admin)
) -> dict[str, Any]:
    """
    Trigger a fresh readiness check.
    """
    service = AgentReadinessService(db)
    return await service.check_readiness()
