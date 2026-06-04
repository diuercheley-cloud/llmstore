import logging
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.models.mobile import MobileDevice, PushNotificationEvent, PushSubscription
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class PushNotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def subscribe(
        self,
        tenant_id: str,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: Optional[str] = None
    ) -> PushSubscription:
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        res = await self.db.execute(stmt)
        sub = res.scalar_one_or_none()

        if sub:
            sub.tenant_id = tenant_id
            sub.user_id = user_id
            sub.p256dh = p256dh
            sub.auth = auth
            sub.is_active = True
        else:
            sub = PushSubscription(
                tenant_id=tenant_id,
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
                is_active=True
            )
            self.db.add(sub)
        
        await self.db.flush()
        logger.info(f"User {user_id} subscribed to push notifications")
        return sub

    async def unsubscribe(self, endpoint: str):
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        res = await self.db.execute(stmt)
        sub = res.scalar_one_or_none()
        if sub:
            sub.is_active = False
            await self.db.flush()
            logger.info("Unsubscribed from push notifications")

    async def send_notification(
        self,
        tenant_id: str,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        if not self.settings.push_notifications_enabled:
            logger.debug("Push notifications disabled by settings")
            return 0

        # Get active subscriptions for user
        stmt = select(PushSubscription).where(
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.user_id == user_id,
            PushSubscription.is_active == True
        )
        res = await self.db.execute(stmt)
        subs = res.scalars().all()

        count = 0
        for sub in subs:
            # In a real implementation, we would use pywebpush or FCM/APNS providers here
            # For now, we'll log the attempt and record an event
            logger.info(f"Simulating push notification to {sub.endpoint}: {title}")
            
            # Record event (optional, linking to device if possible)
            # Find a device for this user to associate the event
            d_stmt = select(MobileDevice).where(
                MobileDevice.tenant_id == tenant_id,
                MobileDevice.user_id == user_id,
                MobileDevice.is_active == True
            ).limit(1)
            d_res = await self.db.execute(d_stmt)
            device = d_res.scalar_one_or_none()

            if device:
                event = PushNotificationEvent(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    device_id=device.id,
                    title=title,
                    body=body,
                    status="sent"
                )
                self.db.add(event)
                count += 1

        await self.db.flush()
        return count
