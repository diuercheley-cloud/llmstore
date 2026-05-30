import uuid
from datetime import datetime
from typing import List, Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.collab_chat import ChatPresenceEvent
from app.core.time import utc_now

class PresenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_presence(self, user_id: str, status: str = "online"):
        stmt = select(ChatPresenceEvent).where(ChatPresenceEvent.user_id == user_id)
        res = await self.db.execute(stmt)
        presence = res.scalar_one_or_none()
        
        if presence:
            presence.status = status
            presence.last_seen_at = utc_now()
        else:
            presence = ChatPresenceEvent(
                user_id=user_id,
                status=status,
                last_seen_at=utc_now()
            )
            self.db.add(presence)
        
        await self.db.flush()
        return presence

    async def get_active_users(self, tenant_id: str) -> List[Dict]:
        # This is simplified. In a real app we might join with users table
        stmt = select(ChatPresenceEvent).where(ChatPresenceEvent.status == "online")
        res = await self.db.execute(stmt)
        return [{"user_id": p.user_id, "status": p.status, "last_seen": p.last_seen_at} for p in res.scalars().all()]
