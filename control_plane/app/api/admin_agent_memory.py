import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session
from app.services.agents.memory.advanced_memory_service import AdvancedMemoryService
from app.models.advanced_memory import MemoryScope, MemoryEventType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/{agent_id}/memory", tags=["admin-agent-memory"])


@router.get("/")
async def list_agent_memory(
    agent_id: uuid.UUID,
    scope: Optional[MemoryScope] = None,
    session: AsyncSession = Depends(get_db_session)
):
    service = AdvancedMemoryService(session)
    await service.compute_forgetting_scores(agent_id)
    memories = await service.list_memories(agent_id, scope)
    
    return [
        {
            "id": str(m.id),
            "scope": m.scope,
            "event_type": m.event_type,
            "payload": m.payload,
            "importance": m.importance_score,
            "decay_score": m.decay_score,
            "access_count": m.access_count,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]


@router.get("/events")
async def list_memory_events(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session)
):
    service = AdvancedMemoryService(session)
    events = await service.get_memory_events(agent_id)
    
    return [
        {
            "id": str(e.id),
            "counter": e.logical_counter,
            "type": e.event_type,
            "hash": e.event_hash,
            "prev_hash": e.previous_event_hash,
            "created_at": e.created_at.isoformat()
        }
        for e in events
    ]


@router.post("/{event_id}/redact")
async def redact_agent_memory(
    agent_id: uuid.UUID,
    event_id: uuid.UUID,
    reason: str = Query(...),
    session: AsyncSession = Depends(get_db_session)
):
    service = AdvancedMemoryService(session)
    await service.redact_memory(event_id, reason)
    return {"status": "success", "message": "Memory redacted"}


@router.post("/{event_id}/forget")
async def forget_agent_memory(
    agent_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session)
):
    service = AdvancedMemoryService(session)
    await service.forget_memory(event_id)
    return {"status": "success", "message": "Memory forgotten"}


@router.post("/compact/dry-run")
async def compaction_dry_run(
    agent_id: uuid.UUID,
    threshold: float = Query(0.1, description="Decay score threshold for removal"),
    session: AsyncSession = Depends(get_db_session)
):
    service = AdvancedMemoryService(session)
    await service.compute_forgetting_scores(agent_id)
    memories = await service.list_memories(agent_id)
    
    to_compact = [m for m in memories if m.decay_score < threshold]
    
    return {
        "agent_id": str(agent_id),
        "total_memories": len(memories),
        "suggested_for_removal": len(to_compact),
        "items": [
            {"id": str(m.id), "scope": m.scope, "decay_score": m.decay_score}
            for m in to_compact
        ]
    }
