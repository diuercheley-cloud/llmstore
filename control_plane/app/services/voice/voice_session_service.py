# Owner: voice-agent
import logging
import uuid

from app.core.time import utc_now
from app.models.core.realtime_voice import VoiceSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VoiceSessionService:
    """Manages voice session lifecycle: create, activate, end, query."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        mode: str = "websocket",
        stt_provider: str = "mock",
        tts_provider: str = "mock",
        language: str = "pt-BR",
    ) -> VoiceSession:
        session = VoiceSession(
            tenant_id=tenant_id,
            agent_id=agent_id,
            mode=mode,
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            language=language,
            status="starting",
        )
        self.db.add(session)
        await self.db.flush()
        logger.info(f"Voice session created: {session.id} tenant={tenant_id} agent={agent_id}")
        return session

    async def get_session(self, session_id: uuid.UUID) -> VoiceSession | None:
        return await self.db.get(VoiceSession, session_id)

    async def activate_session(self, session_id: uuid.UUID) -> VoiceSession | None:
        session = await self.get_session(session_id)
        if session and session.status == "starting":
            session.status = "active"
            await self.db.flush()
        return session

    async def end_session(self, session_id: uuid.UUID) -> VoiceSession | None:
        session = await self.get_session(session_id)
        if session and session.status != "ended":
            session.status = "ended"
            session.ended_at = utc_now()
            await self.db.flush()
            logger.info(f"Voice session ended: {session_id}")
        return session

    async def list_sessions(self, tenant_id: str, limit: int = 50) -> list[VoiceSession]:
        stmt = (
            select(VoiceSession)
            .where(VoiceSession.tenant_id == tenant_id)
            .order_by(VoiceSession.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
