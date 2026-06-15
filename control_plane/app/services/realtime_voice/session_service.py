import uuid

from app.core.time import utc_now
from app.models.core.realtime_voice import VoiceSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class VoiceSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, tenant_id: str, agent_id: uuid.UUID) -> VoiceSession:
        session = VoiceSession(tenant_id=tenant_id, agent_id=agent_id, status="active")
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: uuid.UUID) -> VoiceSession | None:
        return await self.db.get(VoiceSession, session_id)

    async def end_session(self, session_id: uuid.UUID) -> VoiceSession | None:
        session = await self.get_session(session_id)
        if session:
            session.status = "ended"
            session.ended_at = utc_now()
            await self.db.flush()
        return session

    async def list_sessions(self, tenant_id: str) -> list[VoiceSession]:
        stmt = (
            select(VoiceSession)
            .where(VoiceSession.tenant_id == tenant_id)
            .order_by(VoiceSession.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
