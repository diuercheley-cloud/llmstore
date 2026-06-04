# Owner: agent-platform
import uuid
from typing import Any, Dict, List

from app.api.deps import get_db_session, require_admin
from app.services.agents.agent_handoffs import AgentHandoffService
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents", tags=["agent-handoffs"])

@router.post("/handoff-policies")
async def create_handoff_policy(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentHandoffService(db)
    policy = await service.create_handoff_policy(data)
    return {"id": str(policy.id), "status": "created"}

@router.get("/handoff-policies")
async def list_handoff_policies(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    service = AgentHandoffService(db)
    policies = await service.get_handoff_policies(tenant_id)
    return [
        {
            "id": str(p.id),
            "source_agent_id": str(p.source_agent_id),
            "target_agent_id": str(p.target_agent_id),
            "max_handoffs": p.max_handoffs_per_run,
        }
        for p in policies
    ]

@router.get("/runs/{run_id}/handoffs")
async def get_run_handoffs(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    service = AgentHandoffService(db)
    events = await service.list_run_handoffs(run_id)
    return [
        {
            "id": str(e.id),
            "source_run_id": str(e.source_run_id),
            "target_run_id": str(e.target_run_id) if e.target_run_id else None,
            "source_agent_id": str(e.source_agent_id),
            "target_agent_id": str(e.target_agent_id),
            "reason": e.reason,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
