from typing import Optional

from app.api import deps
from app.core.config import get_settings
from app.db.session import get_db
from app.models.client import Client
from app.services.mobile.device_registry import DeviceRegistryService
from app.services.mobile.push_notifications import PushNotificationService
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/mobile", tags=["client", "mobile"])

@router.post("/devices/register")
async def register_device(
    device_token: str = Body(...),
    platform: str = Body(...),
    model: Optional[str] = Body(None),
    app_version: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(deps.require_client),
):
    svc = DeviceRegistryService(db)
    device = await svc.register_device(
        tenant_id=str(client.id),
        user_id=str(client.id), # For now user_id = client_id
        device_token=device_token,
        platform=platform,
        model=model,
        app_version=app_version
    )
    await db.commit()
    return {"id": str(device.id), "status": "registered"}

@router.post("/push/subscribe")
async def subscribe_push(
    endpoint: str = Body(...),
    p256dh: str = Body(...),
    auth: str = Body(...),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(deps.require_client),
    request: Request = None
):
    settings = get_settings()
    if not settings.push_notifications_enabled:
        raise HTTPException(status_code=400, detail="Push notifications are disabled")

    user_agent = request.headers.get("user-agent") if request else None
    svc = PushNotificationService(db)
    await svc.subscribe(
        tenant_id=str(client.id),
        user_id=str(client.id),
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent
    )
    await db.commit()
    return {"status": "subscribed"}

@router.post("/push/unsubscribe")
async def unsubscribe_push(
    endpoint: str = Body(...),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(deps.require_client),
):
    svc = PushNotificationService(db)
    await svc.unsubscribe(endpoint)
    await db.commit()
    return {"status": "unsubscribed"}

@router.get("/config")
async def get_mobile_config():
    settings = get_settings()
    return {
        "push_enabled": settings.push_notifications_enabled,
        "mobile_foundation_enabled": settings.mobile_foundation_enabled,
        "app_version": settings.project_version,
    }
