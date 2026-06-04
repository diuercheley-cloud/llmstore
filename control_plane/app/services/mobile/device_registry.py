import logging
from typing import List, Optional

from app.core.time import utc_now
from app.models.mobile import MobileDevice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class DeviceRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(
        self,
        tenant_id: str,
        user_id: str,
        device_token: str,
        platform: str,
        model: Optional[str] = None,
        app_version: Optional[str] = None,
    ) -> MobileDevice:
        # Check if device already exists
        stmt = select(MobileDevice).where(MobileDevice.device_token == device_token)
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()

        if device:
            # Update existing device
            device.tenant_id = tenant_id
            device.user_id = user_id
            device.platform = platform
            device.model = model
            device.app_version = app_version
            device.is_active = True
            device.updated_at = utc_now()
        else:
            # Create new device
            device = MobileDevice(
                tenant_id=tenant_id,
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                model=model,
                app_version=app_version,
                is_active=True,
            )
            self.db.add(device)

        await self.db.flush()
        logger.info(f"Registered device {device.id} for user {user_id} (platform: {platform})")
        return device

    async def get_user_devices(self, tenant_id: str, user_id: str) -> List[MobileDevice]:
        stmt = select(MobileDevice).where(
            MobileDevice.tenant_id == tenant_id,
            MobileDevice.user_id == user_id,
            MobileDevice.is_active == True
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def deactivate_device(self, device_token: str):
        stmt = select(MobileDevice).where(MobileDevice.device_token == device_token)
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()
        if device:
            device.is_active = False
            await self.db.flush()
            logger.info(f"Deactivated device {device.id}")
