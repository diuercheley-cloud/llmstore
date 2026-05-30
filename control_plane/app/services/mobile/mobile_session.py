import uuid
import secrets
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mobile import MobileSession
from app.core.time import utc_now

class MobileSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, tenant_id: str, user_id: str, device_id: uuid.UUID) -> MobileSession:
        token = secrets.token_urlsafe(64)
        expires_at = utc_now() + timedelta(days=30)
        
        session = MobileSession(
            tenant_id=tenant_id,
            user_id=user_id,
            device_id=device_id,
            session_token=token,
            expires_at=expires_at
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def validate_session(self, token: str) -> bool:
        # Simple lookup
        from sqlalchemy import select
        stmt = select(MobileSession).where(MobileSession.session_token == token)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        
        if not session:
            return False
            
        return session.expires_at > utc_now()
