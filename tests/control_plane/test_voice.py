import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.realtime_voice.audio_stream_service import AudioStreamService
from app.services.realtime_voice.session_service import VoiceSessionService


@pytest.mark.asyncio
async def test_create_voice_session():
    session = AsyncMock()
    svc = VoiceSessionService(session)
    
    tenant_id = "tenant-1"
    agent_id = uuid.uuid4()
    
    voice_session = await svc.create_session(tenant_id, agent_id)
    
    assert voice_session.tenant_id == tenant_id
    assert voice_session.agent_id == agent_id
    assert voice_session.status == "active"

@pytest.mark.asyncio
async def test_audio_mock_generates_transcript():
    session = AsyncMock()
    audio_svc = AudioStreamService(session)
    
    session_id = uuid.uuid4()
    # 42 bytes is the magic number for mock STT to return a transcript
    audio_data = b"\x00" * 42
    
    transcript = await audio_svc.process_audio_chunk(session_id, audio_data)
    assert transcript == "Olá, como posso ajudar?"

@pytest.mark.asyncio
async def test_tts_mock_generates_chunks():
    session = AsyncMock()
    audio_svc = AudioStreamService(session)
    
    session_id = uuid.uuid4()
    text = "Teste de TTS"
    
    audio_gen = await audio_svc.generate_response_audio(session_id, text)
    
    chunks = []
    async for chunk in audio_gen:
        chunks.append(chunk)
        
    assert len(chunks) == 3
    assert chunks[0].startswith(b"AUDIO_CHUNK_")

@pytest.mark.asyncio
async def test_tenant_isolation_voice():
    session = AsyncMock()
    svc = VoiceSessionService(session)
    
    # Mocking select results
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [MagicMock(tenant_id="tenant-1")]
    session.execute.return_value = mock_res
    
    sessions = await svc.list_sessions("tenant-1")
    assert len(sessions) == 1
    assert sessions[0].tenant_id == "tenant-1"
