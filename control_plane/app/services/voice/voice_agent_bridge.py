# Owner: voice-agent
import logging
import uuid
from typing import Optional

from app.core.time import utc_now
from app.models.realtime_voice import VoiceSession, VoiceTranscript, VoiceTurn
from app.services.agents.sessions.agent_session_service import AgentSessionService
from app.services.agents.sessions.conversation_thread_service import ConversationThreadService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VoiceAgentBridge:
    """
    Bridges voice transcripts to the agent session system.

    Flow:
    1. User speaks -> STT produces text
    2. Bridge creates/links agent session
    3. User text becomes agent session message
    4. Agent processes and produces response text
    5. Response text sent to TTS
    6. Transcript persisted for audit
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_agent_session(
        self, voice_session: VoiceSession
    ) -> Optional[uuid.UUID]:
        """Ensure voice session has a linked agent session. Returns agent_session_id."""
        if voice_session.agent_session_id:
            return voice_session.agent_session_id

        session_svc = AgentSessionService(self.db)
        agent_session = await session_svc.create_session(
            tenant_id=voice_session.tenant_id,
            agent_id=voice_session.agent_id,
            user_id=None,
            title=f"Voice session {voice_session.id}",
        )
        voice_session.agent_session_id = agent_session.id
        await self.db.flush()
        logger.info(f"Agent session {agent_session.id} linked to voice session {voice_session.id}")
        return agent_session.id

    async def process_user_turn(
        self,
        voice_session: VoiceSession,
        turn_number: int,
        user_text: str,
    ) -> VoiceTurn:
        """Process a user voice turn: create turn record, send to agent."""
        turn = VoiceTurn(
            session_id=voice_session.id,
            turn_number=turn_number,
            user_text=user_text,
            status="processing",
        )
        self.db.add(turn)
        await self.db.flush()

        # Store user transcript
        transcript = VoiceTranscript(
            session_id=voice_session.id,
            turn_id=turn.id,
            speaker="user",
            text=user_text,
        )
        self.db.add(transcript)

        # Link to agent session and add message
        agent_session_id = await self.ensure_agent_session(voice_session)
        if agent_session_id:
            thread_svc = ConversationThreadService(self.db)
            await thread_svc.add_message(
                session_id=agent_session_id,
                role="user",
                content=user_text,
            )
            await self.db.flush()

        return turn

    async def complete_agent_turn(
        self,
        turn: VoiceTurn,
        agent_text: str,
        agent_run_id: Optional[uuid.UUID] = None,
    ) -> VoiceTurn:
        """Complete an agent turn with the response text."""
        turn.agent_text = agent_text
        turn.agent_run_id = agent_run_id
        turn.status = "completed"
        turn.completed_at = utc_now()

        # Store agent transcript
        transcript = VoiceTranscript(
            session_id=turn.session_id,
            turn_id=turn.id,
            speaker="agent",
            text=agent_text,
        )
        self.db.add(transcript)

        # Add agent response to session thread
        voice_session = await self.db.get(VoiceSession, turn.session_id)
        if voice_session and voice_session.agent_session_id:
            thread_svc = ConversationThreadService(self.db)
            await thread_svc.add_message(
                session_id=voice_session.agent_session_id,
                role="assistant",
                content=agent_text,
                run_id=agent_run_id,
            )

        await self.db.flush()
        return turn

    async def error_turn(
        self,
        turn: VoiceTurn,
        error_message: str,
    ) -> VoiceTurn:
        """Mark a turn as errored."""
        turn.status = "error"
        turn.error_message = error_message
        turn.completed_at = utc_now()
        await self.db.flush()
        return turn

    async def get_transcripts(
        self, session_id: uuid.UUID, limit: int = 100
    ) -> list[VoiceTranscript]:
        """Get all transcripts for a voice session."""
        from sqlalchemy import select
        stmt = (
            select(VoiceTranscript)
            .where(VoiceTranscript.session_id == session_id)
            .order_by(VoiceTranscript.created_at.asc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
