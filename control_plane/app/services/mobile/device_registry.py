import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mobile import MobileDevice

class DeviceRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(
        self,
        tenant_id: str,
        user_id: str,
        device_token: str,
        platform: str,
        model: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> MobileDevice:
        stmt = select(MobileDevice).where(MobileDevice.device_token == device_token)
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()
        
        if device:
            device.tenant_id = tenant_id
            device.user_id = user_id
            device.platform = platform
            device.model = model
            device.app_version = app_version
            device.is_active = True
        else:
            device = MobileDevice(
                tenant_id=tenant_id,
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                model=model,
                app_version=app_version
            )
            self.db.add(device)
            
        await self.db.flush()
        return device

    async def deactivate_device(self, device_token: str):
        stmt = select(MobileDevice).where(MobileDevice.device_token == device_token)
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()
        if device:
            device.is_active = False
            await self.db.flush()
