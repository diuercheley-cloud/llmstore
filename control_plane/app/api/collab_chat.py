import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.services.auth import require_client
from app.models.client import Client
from app.core.config import get_settings
from app.services.collab_chat.channel_service import ChannelService
from app.services.collab_chat.message_service import MessageService
from app.services.collab_chat.presence_service import PresenceService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/chat", tags=["collab_chat"])

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False

class MessageCreate(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

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
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = ChannelService(session)
    return await svc.get_channels(client.id)

@router.post("/channels")
async def create_channel(
    payload: ChannelCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = ChannelService(session)
    channel = await svc.create_channel(client.id, payload.name, payload.description, payload.is_private)
    await svc.add_member(channel.id, client.id, role="admin")
    await session.commit()
    return channel

@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    chan_svc = ChannelService(session)
    if not await chan_svc.is_member(channel_id, client.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    msg_svc = MessageService(session)
    return await msg_svc.get_messages(channel_id)

@router.post("/channels/{channel_id}/messages")
async def post_message(
    channel_id: uuid.UUID,
    payload: MessageCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    chan_svc = ChannelService(session)
    if not await chan_svc.is_member(channel_id, client.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    msg_svc = MessageService(session)
    message = await msg_svc.create_message(channel_id, user_id=client.id, content=payload.content, metadata=payload.metadata)
    await session.commit()
    
    # Broadcast to websocket
    await manager.broadcast(str(channel_id), {
        "type": "new_message",
        "data": {
            "id": str(message.id),
            "user_id": str(message.user_id),
            "content": message.content,
            "created_at": message.created_at.isoformat()
        }
    })
    
    return message

@router.websocket("/channels/{channel_id}/stream")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    channel_id: uuid.UUID,
    token: str, # Basic token check for demo
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
