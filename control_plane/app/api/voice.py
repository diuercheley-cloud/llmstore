import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.services.auth import require_client
from app.models.client import Client
from app.core.config import get_settings
from app.services.realtime_voice.session_service import VoiceSessionService
from app.services.realtime_voice.audio_stream_service import AudioStreamService
from app.services.agents.agent_runtime import start_run

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/voice", tags=["voice"])

class VoiceSessionCreate(BaseModel):
    agent_id: uuid.UUID

class WebRTCOffer(BaseModel):
    session_id: uuid.UUID
    sdp: str
    type: str

def _check_enabled():
    if not settings.realtime_voice_enabled:
        raise HTTPException(status_code=403, detail="Real-time Voice is disabled")

@router.post("/sessions")
async def create_voice_session(
    payload: VoiceSessionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = VoiceSessionService(session)
    voice_session = await svc.create_session(client.id, payload.agent_id)
    await session.commit()
    return voice_session

@router.post("/webrtc/offer")
async def webrtc_offer(
    payload: WebRTCOffer,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    if not settings.webrtc_audio_enabled:
        raise HTTPException(status_code=403, detail="WebRTC Audio is disabled")
    
    # In a real implementation, this would interface with a WebRTC stack (e.g. aiortc)
    # and return an SDP answer.
    return {
        "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=fingerprint:sha-256 ...\r\n",
        "type": "answer"
    }

@router.websocket("/sessions/{session_id}/stream")
async def voice_websocket_stream(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str,
):
    _check_enabled()
    # Basic auth check would go here using token
    
    await websocket.accept()
    
    # We need a db session for the websocket loop
    from app.db.session import SessionLocal
    async with SessionLocal() as db:
        audio_svc = AudioStreamService(db)
        session_svc = VoiceSessionService(db)
        voice_session = await session_svc.get_session(session_id)
        
        if not voice_session:
            await websocket.close(code=4004)
            return

        try:
            while True:
                # Receive audio chunk (binary)
                data = await websocket.receive_bytes()
                
                # Process audio chunk
                transcript = await audio_svc.process_audio_chunk(session_id, data)
                
                if transcript:
                    # If we have a full turn, trigger agent
                    # In a real system, this would be an async call to the agent runtime
                    await websocket.send_json({"type": "transcript", "text": transcript})
                    
                    # Mock response for foundation
                    agent_response = "Entendi. Como posso ajudar com isso?"
                    await websocket.send_json({"type": "agent_response_start", "text": agent_response})
                    
                    audio_gen = await audio_svc.generate_response_audio(session_id, agent_response)
                    async for chunk in audio_gen:
                        await websocket.send_bytes(chunk)
                    
                    await websocket.send_json({"type": "agent_response_end"})
                
                await db.commit()
        except WebSocketDisconnect:
            logger.info(f"Voice session {session_id} disconnected")
        except Exception as e:
            logger.exception(f"Error in voice websocket: {e}")
            await websocket.close(code=1011)
