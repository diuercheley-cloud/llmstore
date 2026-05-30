import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.services.auth import require_client
from app.models.client import Client
from app.core.config import get_settings
from app.services.mobile.device_registry import DeviceRegistry
from app.services.mobile.mobile_session import MobileSessionService
from app.services.mobile.push_notifications import PushNotificationsService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/mobile", tags=["mobile"])


# ── Pydantic schemas ──────────────────────────────────────────────

class DeviceCreate(BaseModel):
    device_token: str
    platform: str
    model: Optional[str] = None
    app_version: Optional[str] = None


class SessionCreate(BaseModel):
    device_token: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────

def _check_enabled():
    if not settings.mobile_foundation_enabled:
        raise HTTPException(status_code=403, detail="Mobile Foundation is disabled")


# ── Device endpoints ──────────────────────────────────────────────

@router.post("/devices")
async def register_device(
    payload: DeviceCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Register or update a mobile/PWA device."""
    _check_enabled()
    svc = DeviceRegistry(session)
    device = await svc.register_device(
        str(client.id), str(client.id), payload.device_token,
        payload.platform, payload.model, payload.app_version
    )
    await session.commit()
    return {
        "id": str(device.id),
        "platform": device.platform,
        "is_active": device.is_active,
        "created_at": device.created_at.isoformat(),
    }


@router.get("/devices")
async def list_devices(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """List all registered devices for this tenant."""
    _check_enabled()
    from app.models.mobile import MobileDevice
    stmt = (
        select(MobileDevice)
        .where(MobileDevice.tenant_id == str(client.id), MobileDevice.is_active == True)
        .order_by(desc(MobileDevice.created_at))
    )
    res = await session.execute(stmt)
    devices = res.scalars().all()
    return [
        {
            "id": str(d.id),
            "platform": d.platform,
            "model": d.model,
            "app_version": d.app_version,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat(),
        }
        for d in devices
    ]


@router.delete("/devices/{device_token}")
async def deactivate_device(
    device_token: str,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Deactivate a device (revoke push access)."""
    _check_enabled()
    from app.models.mobile import MobileDevice
    stmt = select(MobileDevice).where(
        MobileDevice.device_token == device_token,
        MobileDevice.tenant_id == str(client.id),
    )
    res = await session.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_active = False
    await session.commit()
    return {"status": "deactivated"}


# ── Session endpoints ─────────────────────────────────────────────

@router.post("/sessions")
async def start_mobile_session(
    payload: SessionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Start a mobile session for a registered device."""
    _check_enabled()
    from app.models.mobile import MobileDevice
    stmt = select(MobileDevice).where(MobileDevice.device_token == payload.device_token)
    res = await session.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")
    if str(device.tenant_id) != str(client.id):
        raise HTTPException(status_code=403, detail="Device belongs to another tenant")

    svc = MobileSessionService(session)
    mobile_session = await svc.create_session(str(client.id), str(client.id), device.id)
    await session.commit()
    return {
        "session_token": mobile_session.session_token,
        "expires_at": mobile_session.expires_at.isoformat(),
    }


# ── Push subscription endpoints ───────────────────────────────────

@router.post("/push/subscribe")
async def subscribe_push(
    payload: PushSubscriptionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Register a web push subscription (VAPID)."""
    _check_enabled()
    if not settings.push_notifications_enabled:
        raise HTTPException(status_code=403, detail="Push notifications are disabled")

    from app.models.mobile import PushSubscription
    # Upsert by endpoint (one subscription per endpoint per tenant)
    stmt = select(PushSubscription).where(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.tenant_id == str(client.id),
    )
    res = await session.execute(stmt)
    sub = res.scalar_one_or_none()

    if sub:
        sub.p256dh = payload.p256dh
        sub.auth = payload.auth
        sub.user_agent = payload.user_agent
        sub.is_active = True
    else:
        sub = PushSubscription(
            tenant_id=str(client.id),
            user_id=str(client.id),
            endpoint=payload.endpoint,
            p256dh=payload.p256dh,
            auth=payload.auth,
            user_agent=payload.user_agent,
        )
        session.add(sub)

    await session.commit()
    return {"status": "subscribed", "id": str(sub.id)}


@router.delete("/push/subscribe")
async def unsubscribe_push(
    endpoint: str,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Remove a push subscription."""
    _check_enabled()
    from app.models.mobile import PushSubscription
    stmt = select(PushSubscription).where(
        PushSubscription.endpoint == endpoint,
        PushSubscription.tenant_id == str(client.id),
    )
    res = await session.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = False
    await session.commit()
    return {"status": "unsubscribed"}


@router.get("/push/status")
async def push_status(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Check push notification configuration status."""
    return {
        "push_enabled": settings.push_notifications_enabled,
        "mobile_enabled": settings.mobile_foundation_enabled,
    }


# ── Feed / activity ───────────────────────────────────────────────

@router.get("/feed")
async def get_mobile_feed(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Get recent activity feed for mobile."""
    _check_enabled()
    from app.models.agents import AgentRun
    stmt = (
        select(AgentRun)
        .where(AgentRun.tenant_id == str(client.id))
        .order_by(desc(AgentRun.created_at))
        .limit(10)
    )
    res = await session.execute(stmt)
    runs = res.scalars().all()
    return [
        {
            "id": str(run.id),
            "type": "agent_run",
            "title": f"Agent run {run.agent_id}",
            "status": run.status,
            "timestamp": run.created_at.isoformat(),
        }
        for run in runs
    ]


# ── Test endpoint ─────────────────────────────────────────────────

@router.post("/push/test")
async def test_push_notification(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """Send a test push notification."""
    _check_enabled()
    svc = PushNotificationsService(session)
    await svc.send_push(
        str(client.id), str(client.id),
        "Test Notification",
        "This is a test notification from LLM Stack",
    )
    await session.commit()
    return {"status": "sent_if_enabled"}
