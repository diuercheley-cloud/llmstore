# Owner: agent-platform
# Surface: client
import uuid
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.auth import require_client
from app.models.client import Client
from app.services.agents.sessions.agent_session_service import (
    AgentSessionService,
    SessionNotFoundError,
)
from app.services.agents.sessions.conversation_thread_service import (
    ConversationThreadService,
)
from app.services.agents.sessions.session_context_builder import SessionContextBuilder
from app.services.agents.sessions.session_history_policy import (
    SessionHistoryPolicyService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["client", "agents-sessions"])


def _serialize_session(session) -> Dict[str, Any]:
    return {
        "id": str(session.id),
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "agent_id": str(session.agent_id),
        "title": session.title,
        "status": session.status,
        "summary": session.summary,
        "retention_policy": session.retention_policy,
        "metadata": session.session_metadata,
        "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _serialize_message(msg) -> Dict[str, Any]:
    return {
        "id": str(msg.id),
        "thread_id": str(msg.thread_id),
        "session_id": str(msg.session_id),
        "run_id": str(msg.run_id) if msg.run_id else None,
        "role": msg.role,
        "content": msg.content,
        "content_hash": msg.content_hash,
        "metadata": msg.message_metadata,
        "created_at": msg.created_at.isoformat(),
    }


@router.post("/v1/agents/{agent_id}/sessions")
async def create_session(
    agent_id: uuid.UUID,
    title: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
    retention_policy: Optional[Dict[str, Any]] = Body(None),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    session = await svc.create_session(
        tenant_id=str(client.id),
        agent_id=agent_id,
        user_id=None,
        title=title,
        metadata=metadata,
        retention_policy=retention_policy,
    )
    return _serialize_session(session)


@router.get("/v1/agents/sessions")
async def list_sessions(
    agent_id: Optional[uuid.UUID] = Query(None),
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> List[Dict[str, Any]]:
    svc = AgentSessionService(db)
    sessions = await svc.list_sessions(
        tenant_id=str(client.id),
        agent_id=agent_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_serialize_session(s) for s in sessions]


@router.get("/v1/agents/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    session = await svc.get_session(session_id, tenant_id=str(client.id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)


@router.post("/v1/agents/sessions/{session_id}/messages")
async def add_message(
    session_id: uuid.UUID,
    role: str = Body(...),
    content: str = Body(...),
    run_id: Optional[uuid.UUID] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    session = await svc.get_session(session_id, tenant_id=str(client.id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    thread_svc = ConversationThreadService(db)
    message = await thread_svc.add_message(
        session_id=session_id,
        role=role,
        content=content,
        run_id=run_id,
        metadata=metadata,
    )
    await svc.touch_session(session_id)
    
    # Check for automatic summarization
    try:
        await svc.check_and_trigger_summarization(session_id)
    except Exception as e:
        logger.warning(f"Failed to trigger auto-summarization for session {session_id}: {e}")

    await db.commit()
    return _serialize_message(message)


@router.get("/v1/agents/sessions/{session_id}/messages")
async def get_messages(
    session_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> List[Dict[str, Any]]:
    svc = AgentSessionService(db)
    session = await svc.get_session(session_id, tenant_id=str(client.id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    thread_svc = ConversationThreadService(db)
    messages = await thread_svc.get_messages(
        session_id=session_id, limit=limit, offset=offset
    )
    return [_serialize_message(m) for m in messages]


@router.post("/v1/agents/sessions/{session_id}/runs")
async def start_session_run(
    session_id: uuid.UUID,
    input_text: str = Body(...),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    session = await svc.get_session(session_id, tenant_id=str(client.id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    from app.services.agents import agent_state

    run = await agent_state.create_agent_run(
        db=db,
        agent_id=session.agent_id,
        tenant_id=str(client.id),
        input_text=input_text,
        user_id=session.user_id,
        session_id=session_id,
    )

    await svc.link_run_to_session(session_id, run.id)
    await svc.touch_session(session_id)

    thread_svc = ConversationThreadService(db)
    await thread_svc.add_message(
        session_id=session_id,
        role="user",
        content=input_text,
        run_id=run.id,
    )
    await db.commit()

    return {
        "run_id": str(run.id),
        "session_id": str(session_id),
        "status": run.status,
    }


@router.delete("/v1/agents/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    deleted = await svc.delete_session(session_id, tenant_id=str(client.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": str(session_id)}


@router.patch("/v1/agents/sessions/{session_id}")
async def update_session(
    session_id: uuid.UUID,
    title: Optional[str] = Body(None),
    status: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    svc = AgentSessionService(db)
    session = await svc.update_session(
        session_id=session_id,
        tenant_id=str(client.id),
        title=title,
        status=status,
        metadata=metadata,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)
