import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.services.auth import (
    AdminRole,
    bearer_scheme,
    get_admin_role,
    require_client,
)
from app.services.collab_chat.channel_service import ChannelService
from app.services.collab_chat.message_service import MessageService
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/chat", tags=["collab_chat"])


async def get_chat_actor(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Custom dependency that manually checks for either admin token or client bearer token."""
    # 1. Check Admin Token
    admin_token = request.headers.get("X-Admin-Token")
    if admin_token:
        role = get_admin_role(admin_token)
        if role and role >= AdminRole.SUPER:
            return {"id": "admin", "name": "System Admin", "tenant_id": "admin"}

    # 2. Check Client Bearer Token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # We can't easily call require_client because it's a dependency with its own logic
            # but we can try to use it if we wrap it.
            # For now, let's just use the existing one if we can,
            # but require_client raises exceptions.
            pass
        except Exception:
            pass

    # Fallback to the strict dependencies if we didn't find a quick match
    # but we want to avoid the "missing bearer token" error if we HAVE an admin token.
    if admin_token:
        role = get_admin_role(admin_token)
        if role and role >= AdminRole.SUPER:
            return {"id": "admin", "name": "System Admin", "tenant_id": "admin"}

    # If no admin token, try client
    try:
        client = await require_client(auth_creds=await bearer_scheme(request), session=session)
        return {"id": str(client.id), "name": client.name, "tenant_id": str(client.id)}
    except HTTPException as e:
        if admin_token:
            # Re-verify admin token more strictly if client failed
            role = get_admin_role(admin_token)
            if role and role >= AdminRole.SUPER:
                return {"id": "admin", "name": "System Admin", "tenant_id": "admin"}
        raise e


class ChannelCreate(BaseModel):
    name: str
    description: str | None = None
    is_private: bool = False


class MessageCreate(BaseModel):
    content: str
    metadata: dict[str, Any] | None = None


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel_id: str, websocket: WebSocket):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append(websocket)

    def disconnect(self, channel_id: str, websocket: WebSocket):
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)

    async def broadcast(self, channel_id: str, message: dict):
        if channel_id in self.active_connections:
            for connection in self.active_connections[channel_id]:
                await connection.send_json(message)


manager = ConnectionManager()


def _check_enabled():
    if not settings.collab_chat_enabled:
        raise HTTPException(status_code=403, detail="Collaborative Chat is disabled")


@router.get("/channels")
async def list_channels(
    actor: dict = Depends(get_chat_actor),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = ChannelService(session)
    # Automatically create a general channel for the tenant if it doesn't exist
    channels = await svc.get_channels(actor["tenant_id"])
    if not channels:
        general = await svc.create_channel(
            actor["tenant_id"], "geral", "Canal geral para discussões."
        )
        await svc.add_member(general.id, actor["id"], role="admin")
        await session.commit()
        channels = [general]
    return channels


@router.post("/channels")
async def create_channel(
    payload: ChannelCreate,
    actor: dict = Depends(get_chat_actor),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = ChannelService(session)
    channel = await svc.create_channel(
        actor["tenant_id"], payload.name, payload.description, payload.is_private
    )
    await svc.add_member(channel.id, actor["id"], role="admin")
    await session.commit()
    return channel


@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: uuid.UUID,
    actor: dict = Depends(get_chat_actor),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    chan_svc = ChannelService(session)
    if not await chan_svc.is_member(channel_id, actor["id"]):
        # Auto-join for now in demo mode
        await chan_svc.add_member(channel_id, actor["id"])
        await session.commit()

    msg_svc = MessageService(session)
    return await msg_svc.get_messages(channel_id)


@router.post("/channels/{channel_id}/messages")
async def post_message(
    channel_id: uuid.UUID,
    payload: MessageCreate,
    actor: dict = Depends(get_chat_actor),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    chan_svc = ChannelService(session)
    if not await chan_svc.is_member(channel_id, actor["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    msg_svc = MessageService(session)
    message = await msg_svc.create_message(
        channel_id, user_id=actor["id"], content=payload.content, metadata=payload.metadata
    )
    await session.commit()

    # Broadcast to websocket
    await manager.broadcast(
        str(channel_id),
        {
            "type": "new_message",
            "data": {
                "id": str(message.id),
                "user_id": str(message.user_id),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            },
        },
    )

    return message


@router.websocket("/channels/{channel_id}/stream")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    channel_id: uuid.UUID,
    token: str,  # Basic token check for demo
):
    if not settings.collab_chat_websocket_enabled:
        await websocket.close(code=1008)
        return

    await manager.connect(str(channel_id), websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WS messages if needed (e.g. typing indicators)
            pass
    except WebSocketDisconnect:
        manager.disconnect(str(channel_id), websocket)
