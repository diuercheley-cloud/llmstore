import uuid

import pytest
from app.models.agents.agent_sessions import AgentSession
from app.models.core.realtime_voice import VoiceSession, VoiceTranscript, VoiceTurn
from app.services.voice.stt_stream_service import STTStreamService
from app.services.voice.tts_stream_service import TTSStreamService
from app.services.voice.voice_agent_bridge import VoiceAgentBridge
from app.services.voice.voice_session_service import VoiceSessionService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_voice_session_lifecycle(session: AsyncSession):
    svc = VoiceSessionService(session)
    tenant_id = "test-tenant"
    agent_id = uuid.uuid4()

    # 1. Create Session
    v_session = await svc.create_session(tenant_id=tenant_id, agent_id=agent_id, mode="websocket")
    assert v_session.id is not None
    assert v_session.status == "starting"

    # 2. Activate
    await svc.activate_session(v_session.id)
    assert v_session.status == "active"

    # 3. List
    sessions = await svc.list_sessions(tenant_id)
    assert len(sessions) == 1

    # 4. End
    await svc.end_session(v_session.id)
    assert v_session.status == "ended"
    assert v_session.ended_at is not None


@pytest.mark.asyncio
async def test_voice_agent_bridge(session: AsyncSession):
    from app.models.agents.agents import AgentDefinition

    # Setup: need an agent definition
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Voice Agent",
        version="1.0.0",
        tenant_id="test-tenant",
        instructions="You are a voice assistant",
        model_id="gpt-4",
        owner="test",
    )
    session.add(agent)
    await session.flush()

    bridge = VoiceAgentBridge(session)
    v_session = VoiceSession(tenant_id="test-tenant", agent_id=agent.id, status="active")
    session.add(v_session)
    await session.flush()

    # 1. Process User Turn (STT Result)
    user_text = "Hello voice agent"
    turn = await bridge.process_user_turn(v_session, 1, user_text)

    assert turn.user_text == user_text
    assert turn.status == "processing"
    assert v_session.agent_session_id is not None

    # Verify transcript stored
    transcript = await bridge.get_transcripts(v_session.id)
    assert len(transcript) == 1
    assert transcript[0].text == user_text
    assert transcript[0].speaker == "user"

    # Verify agent session message
    agent_session = await session.get(AgentSession, v_session.agent_session_id)
    assert agent_session is not None

    # 2. Complete Agent Turn (TTS Ready)
    agent_text = "Hello! How can I help you today?"
    await bridge.complete_agent_turn(turn, agent_text)

    assert turn.status == "completed"
    assert turn.agent_text == agent_text

    # Verify second transcript
    transcripts = await bridge.get_transcripts(v_session.id)
    assert len(transcripts) == 2
    assert transcripts[1].text == agent_text
    assert transcripts[1].speaker == "agent"


@pytest.mark.asyncio
async def test_stt_tts_mock(session: AsyncSession):
    stt = STTStreamService(provider="mock")
    tts = TTSStreamService(provider="mock")

    # STT Mock test
    res = await stt.feed_audio(b"1" * 42)  # 42 byte trigger
    assert res == "Ola, como posso ajudar?"

    # TTS Mock test
    chunks = []
    async for chunk in tts.synthesize("Test response"):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0] == b"AUDIO_CHUNK_0_DATA"


@pytest.mark.asyncio
async def test_audio_non_persistence(session: AsyncSession):
    # Ensure raw audio is not in models
    # We check VoiceTurn and VoiceTranscript for large blob columns
    from sqlalchemy import inspect

    for model in [VoiceTurn, VoiceTranscript]:
        mapper = inspect(model)
        for column in mapper.columns:
            # Check for LargeBinary or similar
            col_type = str(column.type).lower()
            assert "blob" not in col_type
            assert "bytea" not in col_type
            assert "binary" not in col_type
