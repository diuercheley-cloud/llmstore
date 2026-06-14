# Owner: voice-agent
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.core.realtime_voice import VoiceSession, VoiceStreamEvent, VoiceTurn
from app.models.agents.agents import AgentMemoryItem
from app.models.agents.agent_sessions import AgentThreadMessage
from app.services.voice.voice_turn_service import VoiceTurnService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_voice_turn_service_success(session: AsyncSession):
    # Setup
    v_session = VoiceSession(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        agent_id=uuid.uuid4(),
        agent_session_id=uuid.uuid4(),
        status="active"
    )
    session.add(v_session)
    await session.flush()

    turn_svc = VoiceTurnService(session)
    
    # Mock agent_runtime.start_run
    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    mock_run.status = "completed"
    
    # Mock Memory Item
    from app.core.time import utc_now
    from datetime import timedelta
    memory_item = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        agent_id=v_session.agent_id,
        memory_type="short_term",
        raw_content="Response from memory",
        content_hash="mock-hash",
        source_run_id=mock_run.id,
        retention_until=utc_now() + timedelta(days=1)
    )
    session.add(memory_item)
    await session.flush()

    with patch("app.services.agents.agent_runtime.start_run", new_callable=AsyncMock) as mock_start_run:
        mock_start_run.return_value = mock_run
        
        result = await turn_svc.process_turn(
            voice_session=v_session,
            turn_number=1,
            transcript_text="Hello agent",
            correlation_id="test-trace"
        )
        
        assert result["text"] == "Response from memory"
        assert result["agent_run_id"] == str(mock_run.id)
        assert result["correlation_id"] == "test-trace"
        assert result["fallback"] is False
        
        # Verify audit events
        stmt = select(VoiceStreamEvent).where(VoiceStreamEvent.session_id == v_session.id)
        res = await session.execute(stmt)
        events = res.scalars().all()
        
        event_types = [e.event_type for e in events]
        assert "voice_turn_started" in event_types
        assert "voice_turn_completed" in event_types

@pytest.mark.asyncio
async def test_voice_turn_service_fallback_on_runtime_failure(session: AsyncSession):
    # Setup
    v_session = VoiceSession(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        agent_id=uuid.uuid4(),
        agent_session_id=uuid.uuid4(),
        status="active"
    )
    session.add(v_session)
    await session.flush()

    turn_svc = VoiceTurnService(session)
    
    with patch("app.services.agents.agent_runtime.start_run", side_effect=Exception("Runtime error")):
        result = await turn_svc.process_turn(
            voice_session=v_session,
            turn_number=1,
            transcript_text="Hello agent"
        )
        
        assert "problema técnico" in result["text"]
        assert result["fallback"] is True
        
        # Verify audit events
        stmt = select(VoiceStreamEvent).where(VoiceStreamEvent.session_id == v_session.id)
        res = await session.execute(stmt)
        events = res.scalars().all()
        
        event_types = [e.event_type for e in events]
        assert "voice_turn_failed" in event_types
        assert "voice_turn_fallback_used" in event_types

@pytest.mark.asyncio
async def test_voice_turn_service_from_thread_if_memory_missing(session: AsyncSession):
    # Setup
    v_session = VoiceSession(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        agent_id=uuid.uuid4(),
        agent_session_id=uuid.uuid4(),
        status="active"
    )
    session.add(v_session)
    await session.flush()

    turn_svc = VoiceTurnService(session)
    
    # Mock agent_runtime.start_run
    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    mock_run.status = "completed"
    
    # Mock Thread Message (but NO Memory Item)
    thread_msg = AgentThreadMessage(
        id=uuid.uuid4(),
        session_id=v_session.agent_session_id,
        thread_id=uuid.uuid4(), # Should really be session's thread
        run_id=mock_run.id,
        role="assistant",
        content="Response from thread"
    )
    # We need to make sure the thread exists or handle default thread
    # Simplification: just add it to DB and use the query in the service
    session.add(thread_msg)
    await session.flush()

    with patch("app.services.agents.agent_runtime.start_run", new_callable=AsyncMock) as mock_start_run:
        mock_start_run.return_value = mock_run
        
        result = await turn_svc.process_turn(
            voice_session=v_session,
            turn_number=1,
            transcript_text="Hello agent"
        )
        
        assert result["text"] == "Response from thread"
        assert result["fallback"] is False
