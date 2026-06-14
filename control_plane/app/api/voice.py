# Owner: voice-agent
import json
import logging
import uuid
from typing import Optional

from app.core.config import get_settings
from app.services.runtime_dependencies import SessionLocal, get_db_session
from app.models.core.client import Client
from app.services.auth import require_client
from app.services.voice.stt_stream_service import STTStreamService
from app.services.voice.tts_stream_service import TTSStreamService
from app.services.voice.turn_detection import TurnDetectionService
from app.services.voice.voice_agent_bridge import VoiceAgentBridge
from app.services.voice.voice_turn_service import VoiceTurnService
from app.services.voice.voice_session_service import VoiceSessionService
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/voice", tags=["voice-agent"])


# ── Pydantic schemas ──────────────────────────────────────────────

class VoiceSessionCreate(BaseModel):
    agent_id: uuid.UUID
    mode: str = "websocket"
    stt_provider: str = "local_whisper_real"
    tts_provider: str = "local_tts_real"
    language: str = "pt-BR"


class WebRTCOffer(BaseModel):
    session_id: uuid.UUID
    sdp: str
    type: str


# ── Feature flag checks ───────────────────────────────────────────

def _check_voice_agent():
    if not settings.voice_agent_enabled:
        raise HTTPException(status_code=403, detail="Voice Agent is disabled")


def _check_webrtc():
    if not settings.webrtc_voice_enabled:
        raise HTTPException(status_code=403, detail="WebRTC Voice is disabled")


# ── REST Endpoints ────────────────────────────────────────────────

@router.post("/sessions")
async def create_voice_session(
    payload: VoiceSessionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new voice session linked to an agent."""
    _check_voice_agent()

    svc = VoiceSessionService(session)
    voice_session = await svc.create_session(
        tenant_id=str(client.id),
        agent_id=payload.agent_id,
        mode=payload.mode,
        stt_provider=payload.stt_provider,
        tts_provider=payload.tts_provider,
        language=payload.language,
    )
    await session.commit()

    return {
        "id": str(voice_session.id),
        "status": voice_session.status,
        "mode": voice_session.mode,
        "agent_id": str(voice_session.agent_id),
        "created_at": voice_session.created_at.isoformat(),
    }


@router.get("/sessions")
async def list_voice_sessions(
    limit: int = Query(50, ge=1, le=200),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """List voice sessions for this tenant."""
    _check_voice_agent()
    svc = VoiceSessionService(session)
    sessions = await svc.list_sessions(str(client.id), limit)
    return [
        {
            "id": str(s.id),
            "agent_id": str(s.agent_id),
            "status": s.status,
            "mode": s.mode,
            "created_at": s.created_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_voice_session(
    session_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Get a voice session by ID."""
    _check_voice_agent()
    svc = VoiceSessionService(session)
    voice_session = await svc.get_session(session_id)
    if not voice_session or voice_session.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Voice session not found")
    return {
        "id": str(voice_session.id),
        "agent_id": str(voice_session.agent_id),
        "status": voice_session.status,
        "mode": voice_session.mode,
        "stt_provider": voice_session.stt_provider,
        "tts_provider": voice_session.tts_provider,
        "language": voice_session.language,
        "created_at": voice_session.created_at.isoformat(),
        "ended_at": voice_session.ended_at.isoformat() if voice_session.ended_at else None,
    }


@router.delete("/sessions/{session_id}")
async def end_voice_session(
    session_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """End a voice session."""
    _check_voice_agent()
    svc = VoiceSessionService(session)
    voice_session = await svc.get_session(session_id)
    if not voice_session or voice_session.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Voice session not found")
    await svc.end_session(session_id)
    await session.commit()
    return {"status": "ended"}


@router.post("/webrtc/offer")
async def webrtc_offer(
    payload: WebRTCOffer,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Handle WebRTC SDP offer for voice (signaling only)."""
    _check_voice_agent()
    _check_webrtc()

    svc = VoiceSessionService(session)
    voice_session = await svc.get_session(payload.session_id)
    if not voice_session or voice_session.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Voice session not found")

    # Placeholder: real implementation would use aiortc or Janus
    return {
        "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n",
        "type": "answer",
        "session_id": str(payload.session_id),
    }


# ── WebSocket Stream ──────────────────────────────────────────────

@router.websocket("/sessions/{session_id}/stream")
async def voice_websocket_stream(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time voice streaming.

    Protocol:
    - Client sends: binary (audio chunks) or JSON control messages
    - Server sends: JSON events (transcript, agent_response, tts_audio, turn_status)

    Client -> Server:
      Binary: raw audio data (PCM/Opus)
      JSON: {"type": "end_turn"} - user finished speaking
      JSON: {"type": "cancel"} - cancel current processing

    Server -> Client:
      {"type": "session_ready", "session_id": "..."}
      {"type": "transcript", "text": "...", "speaker": "user"}
      {"type": "agent_thinking"}
      {"type": "agent_response", "text": "..."}
      {"type": "tts_audio_start"}
      Binary: audio chunk from TTS
      {"type": "tts_audio_end"}
      {"type": "turn_complete", "turn_number": 1}
      {"type": "error", "message": "..."}
    """
    # Feature flag
    if not settings.voice_agent_enabled:
        await websocket.close(code=4003, reason="Voice Agent disabled")
        return

    # Parse session_id
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        await websocket.close(code=4004, reason="Invalid session ID")
        return

    # Accept first, authenticate via token
    await websocket.accept()

    # Authenticate
    async with SessionLocal() as db:
        # Token-based auth (simplified for WebSocket)
        if token:
            from app.services.agents.streaming.stream_auth import StreamAuthService
            try:
                client = await StreamAuthService.authenticate_websocket(websocket, db)
            except Exception:
                return
        else:
            await websocket.close(code=4001, reason="Missing token")
            return

        # Load voice session
        svc = VoiceSessionService(db)
        voice_session = await svc.get_session(session_uuid)
        if not voice_session:
            await websocket.close(code=4004, reason="Voice session not found")
            return
        if voice_session.tenant_id != str(client.id):
            await websocket.close(code=4003, reason="Tenant mismatch")
            return

        # Activate session
        await svc.activate_session(session_uuid)
        await db.commit()

        # Initialize services
        stt = STTStreamService(
            provider=voice_session.stt_provider,
            language=voice_session.language,
        )
        tts = TTSStreamService(provider=voice_session.tts_provider)
        vad = TurnDetectionService()
        bridge = VoiceAgentBridge(db)
        turn_svc = VoiceTurnService(db)

        turn_number = 0
        current_turn = None

        try:
            await websocket.send_json({
                "type": "session_ready",
                "session_id": str(session_uuid),
                "stt_provider": voice_session.stt_provider,
                "tts_provider": voice_session.tts_provider,
            })

            while True:
                data = await websocket.receive()

                if "bytes" in data:
                    audio_chunk = data["bytes"]

                    # VAD check
                    is_speech = await vad.is_speech(audio_chunk)

                    # STT processing
                    transcript_text = await stt.feed_audio(audio_chunk)

                    if transcript_text:
                        # New turn starts
                        if current_turn is None or current_turn.status in ("completed", "error"):
                            turn_number += 1
                            current_turn = await bridge.process_user_turn(
                                voice_session, turn_number, transcript_text
                            )
                            await db.commit()

                        await websocket.send_json({
                            "type": "transcript",
                            "text": transcript_text,
                            "speaker": "user",
                            "turn_number": turn_number,
                        })

                    # Turn boundary detection
                    if current_turn and current_turn.status == "processing":
                        is_complete = await vad.is_turn_complete(audio_chunk)
                        if is_complete:
                            # User finished speaking - get agent response
                            await websocket.send_json({"type": "agent_thinking"})

                            # Real implementation calling agent_runtime via VoiceTurnService
                            from app.core.request_context import get_correlation_id
                            correlation_id = get_correlation_id() or str(uuid.uuid4())

                            turn_result = await turn_svc.process_turn(
                                voice_session=voice_session,
                                turn_number=turn_number,
                                transcript_text=current_turn.user_text,
                                correlation_id=correlation_id
                            )
                            
                            agent_text = turn_result["text"]
                            agent_run_id = turn_result["agent_run_id"]

                            await websocket.send_json({
                                "type": "agent_response",
                                "text": agent_text,
                                "turn_number": turn_number,
                                "agent_run_id": agent_run_id,
                                "correlation_id": correlation_id,
                                "trace_id": correlation_id,
                                "fallback": turn_result["fallback"]
                            })

                            # TTS streaming
                            if settings.voice_tts_streaming_enabled:
                                await websocket.send_json({"type": "tts_audio_start"})
                                async for audio_chunk in tts.synthesize(
                                    agent_text,
                                    tenant_id=str(client.id),
                                ):
                                    await websocket.send_bytes(audio_chunk)
                                await websocket.send_json({"type": "tts_audio_end"})

                            await websocket.send_json({
                                "type": "turn_complete",
                                "turn_number": turn_number,
                            })

                            # Reset for next turn
                            vad.reset()
                            stt.reset()
                            current_turn = None

                elif "text" in data:
                    # JSON control message
                    try:
                        msg = json.loads(data["text"])
                    except json.JSONDecodeError:
                        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                        continue

                    msg_type = msg.get("type")

                    if msg_type == "cancel":
                        if current_turn and current_turn.status == "processing":
                            current_turn = await bridge.error_turn(current_turn, "Cancelled by user")
                            await db.commit()
                        vad.reset()
                        stt.reset()
                        current_turn = None
                        await websocket.send_json({"type": "cancelled"})

                    elif msg_type == "end_turn":
                        # Force turn end
                        if current_turn and current_turn.status == "processing":
                            user_text = current_turn.user_text or ""
                            agent_text = f"Processando: '{user_text}'"
                            current_turn = await bridge.complete_agent_turn(current_turn, agent_text)
                            await db.commit()

                            await websocket.send_json({
                                "type": "agent_response",
                                "text": agent_text,
                                "turn_number": turn_number,
                            })

                            if settings.voice_tts_streaming_enabled:
                                await websocket.send_json({"type": "tts_audio_start"})
                                async for audio_chunk in tts.synthesize(agent_text, tenant_id=str(client.id)):
                                    await websocket.send_bytes(audio_chunk)
                                await websocket.send_json({"type": "tts_audio_end"})

                            await websocket.send_json({"type": "turn_complete", "turn_number": turn_number})

                        vad.reset()
                        stt.reset()
                        current_turn = None

                    else:
                        await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

        except WebSocketDisconnect:
            logger.info(f"Voice session {session_id} disconnected")
        except Exception as e:
            logger.exception(f"Voice WebSocket error: {e}")
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            # End session
            await svc.end_session(session_uuid)
            await db.commit()
