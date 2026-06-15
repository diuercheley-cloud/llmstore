import uuid
from typing import Any

from app.services.assistants.assistant_registry import AssistantRegistry
from app.services.assistants.assistant_run_adapter import AssistantRunAdapter
from app.services.assistants.message_store import MessageStore
from app.services.assistants.thread_store import ThreadStore
from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1", tags=["Assistants API V1 Compatibility"])

# --- Schemas ---


class AssistantCreate(BaseModel):
    name: str
    model: str
    instructions: str
    description: str | None = None
    tools: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class MessageCreate(BaseModel):
    role: str
    content: str
    metadata: dict[str, Any] | None = None


class RunCreate(BaseModel):
    assistant_id: uuid.UUID
    instructions: str | None = None
    tools: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


# --- Endpoints ---


@router.post("/assistants")
async def create_assistant(
    data: AssistantCreate,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    registry = AssistantRegistry(db)
    assistant = await registry.create_assistant(
        tenant_id=tenant_id,
        name=data.name,
        model_id=data.model,
        instructions=data.instructions,
        description=data.description,
        tools=data.tools,
        metadata=data.metadata,
    )
    await db.commit()
    return {
        "id": str(assistant.id),
        "object": "assistant",
        "created_at": int(assistant.created_at.timestamp()),
    }


@router.get("/assistants")
async def list_assistants(
    tenant_id: str = Header(..., alias="X-Tenant-ID"), db: AsyncSession = Depends(get_db)
):
    registry = AssistantRegistry(db)
    assistants = await registry.list_assistants(tenant_id)
    return {"object": "list", "data": [{"id": str(a.id), "name": a.name} for a in assistants]}


@router.post("/threads")
async def create_thread(
    tenant_id: str = Header(..., alias="X-Tenant-ID"), db: AsyncSession = Depends(get_db)
):
    store = ThreadStore(db)
    thread = await store.create_thread(tenant_id)
    await db.commit()
    return {
        "id": str(thread.id),
        "object": "thread",
        "created_at": int(thread.created_at.timestamp()),
    }


@router.post("/threads/{thread_id}/messages")
async def add_message(
    thread_id: uuid.UUID,
    data: MessageCreate,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    t_store = ThreadStore(db)
    thread = await t_store.get_thread(tenant_id, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    m_store = MessageStore(db)
    message = await m_store.add_message(
        thread_id=thread_id, role=data.role, content=data.content, metadata=data.metadata
    )
    await db.commit()
    return {
        "id": str(message.id),
        "object": "thread.message",
        "created_at": int(message.created_at.timestamp()),
    }


@router.post("/threads/{thread_id}/runs")
async def create_run(
    thread_id: uuid.UUID,
    data: RunCreate,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    adapter = AssistantRunAdapter(db)
    run = await adapter.create_run(
        tenant_id=tenant_id,
        thread_id=thread_id,
        assistant_id=data.assistant_id,
        instructions=data.instructions,
        tools=data.tools,
        metadata=data.metadata,
    )
    await db.commit()
    return {
        "id": str(run.id),
        "object": "thread.run",
        "status": run.status,
        "assistant_id": str(data.assistant_id),
    }


@router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(
    thread_id: uuid.UUID,
    run_id: uuid.UUID,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    adapter = AssistantRunAdapter(db)
    run = await adapter.get_run(tenant_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": str(run.id), "object": "thread.run", "status": run.status}
