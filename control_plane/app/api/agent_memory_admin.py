# Owner: agent-platform
import uuid
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.models.agents.agents import AgentMemoryAccessEvent, AgentMemoryItem
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.memory_consent import MemoryConsentService
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents.memory_retention import MemoryRetentionService
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/memory", tags=["agent-memory"])


@router.get("/policies")
async def list_policies(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
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
) -> dict[str, Any]:
    service = MemoryPolicyService(db)
    policy = await service.create_policy(data)
    return {"id": str(policy.id), "status": "created"}


@router.get("/consents")
async def list_consents(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    service = MemoryConsentService(db)
    consents = await service.list_consents(tenant_id)
    return [
        {
            "id": str(c.id),
            "tenant_id": c.tenant_id,
            "user_id": c.user_id,
            "agent_id": str(c.agent_id) if c.agent_id else None,
            "memory_type": c.memory_type,
            "status": c.status,
            "granted_at": c.granted_at.isoformat() if c.granted_at else None,
        }
        for c in consents
    ]


@router.post("/consents")
async def create_consent(
    tenant_id: str = Body(...),
    user_id: str = Body(...),
    memory_type: str = Body(...),
    agent_id: uuid.UUID | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = MemoryConsentService(db)
    consent = await service.create_consent(tenant_id, user_id, memory_type, agent_id)
    return {"id": str(consent.id), "status": "created"}


@router.post("/search")
async def search_memory(
    tenant_id: str = Body(...),
    agent_id: uuid.UUID = Body(...),
    query: str = Body(...),
    limit: int = Body(10),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    service = AgentMemoryService(db)
    items = await service.search_memory(tenant_id, agent_id, query, limit)
    return [
        {
            "id": str(item.id),
            "agent_id": str(item.agent_id),
            "memory_type": item.memory_type,
            "content": item.raw_content,
            "summary": item.summary,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@router.post("/export")
async def export_memory(
    tenant_id: str = Body(...),
    agent_id: uuid.UUID | None = Body(None),
    memory_type: str | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    service = AgentMemoryService(db)
    return await service.export_memory(tenant_id, agent_id, memory_type)


@router.post("/delete-request")
async def create_delete_request(
    tenant_id: str = Body(...),
    agent_id: uuid.UUID | None = Body(None),
    memory_type: str | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = MemoryRetentionService(db)
    req = await service.create_delete_request(tenant_id, agent_id, memory_type)
    return {"id": str(req.id), "status": "pending"}


@router.post("/retention/run")
async def run_retention(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = MemoryRetentionService(db)
    ret_res = await service.run_retention()
    del_res = await service.process_delete_requests()
    return {"retention": ret_res, "delete_requests": del_res}


@router.get("/access-events")
async def get_access_events(
    tenant_id: str,
    agent_id: uuid.UUID | None = None,
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    stmt = select(AgentMemoryAccessEvent).where(AgentMemoryAccessEvent.tenant_id == tenant_id)
    if agent_id:
        stmt = stmt.where(AgentMemoryAccessEvent.agent_id == agent_id)
    stmt = stmt.order_by(AgentMemoryAccessEvent.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    events = res.scalars().all()
    return [
        {
            "id": str(e.id),
            "agent_id": str(e.agent_id),
            "run_id": str(e.run_id) if e.run_id else None,
            "memory_item_id": str(e.memory_item_id),
            "operation": e.operation,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/items")
async def list_memory_items(
    tenant_id: str,
    agent_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
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
) -> dict[str, Any]:
    service = AgentMemoryService(db)
    await service.delete_memory_item(tenant_id, item_id)
    return {"status": "deleted"}
