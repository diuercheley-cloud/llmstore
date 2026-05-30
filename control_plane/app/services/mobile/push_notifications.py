import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mobile import PushNotificationEvent, MobileDevice
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class PushNotificationsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_push(
        self,
        tenant_id: str,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ):
        if not settings.push_notifications_enabled:
            logger.info("Push notifications are disabled")
            return

        # 1. Find active devices for user
        from sqlalchemy import select
        stmt = select(MobileDevice).where(
            MobileDevice.user_id == user_id,
            MobileDevice.is_active == True
        )
        res = await self.db.execute(stmt)
        devices = res.scalars().all()

        for device in devices:
            # 2. Mock sending to FCM/APNs
            logger.info(f"Sending push to {device.platform} device {device.id}: {title}")
            
            # 3. Record event
            event = PushNotificationEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                device_id=device.id,
                title=title,
                body=body,
                status="sent"
            )
            self.db.add(event)
        
        await self.db.flush()
