import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import require_admin, get_db_session
from app.models.agents import AgentMemoryPolicy, AgentMemoryItem
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents.agent_memory import AgentMemoryService

router = APIRouter(prefix="/admin/agent-memory", tags=["agent-memory"])

@router.get("/policies")
async def list_policies(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    service = MemoryPolicyService(db)
    policies = await service.list_policies(tenant_id)
    return [
        {
            "id": str(p.id),
            "tenant_id": p.tenant_id,
            "agent_id": str(p.agent_id) if p.agent_id else None,
            "memory_type": p.memory_type,
            "retention_days": p.retention_days,
            "redaction_enabled": p.redaction_enabled,
        }
        for p in policies
    ]

@router.post("/policies")
async def create_policy(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = MemoryPolicyService(db)
    policy = await service.create_policy(data)
    return {"id": str(policy.id), "status": "created"}

@router.get("/items")
async def list_memory_items(
    tenant_id: str,
    agent_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    stmt = select(AgentMemoryItem).where(AgentMemoryItem.tenant_id == tenant_id)
    if agent_id:
        stmt = stmt.where(AgentMemoryItem.agent_id == agent_id)
    
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [
        {
            "id": str(item.id),
            "agent_id": str(item.agent_id),
            "memory_type": item.memory_type,
            "summary": item.summary,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]

@router.delete("/items/{item_id}")
async def delete_memory_item(
    item_id: uuid.UUID,
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentMemoryService(db)
    await service.delete_memory_item(tenant_id, item_id)
    return {"status": "deleted"}

@router.post("/export")
async def export_memory(
    tenant_id: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    service = AgentMemoryService(db)
    return await service.export_memory(tenant_id)

@router.get("/agents/{agent_id}/memory")
async def get_agent_memory(
    agent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    # This might be used by the agent itself or the client
    # For now, let's assume it needs a tenant_id from headers or session
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    service = AgentMemoryService(db)
    items = await service.read_memory(tenant_id, agent_id)
    return [
        {
            "id": str(item.id),
            "type": item.memory_type,
            "content": item.raw_content,
            "summary": item.summary,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
