import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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

class DeviceCreate(BaseModel):
    device_token: str
    platform: str
    model: Optional[str] = None
    app_version: Optional[str] = None

class SessionCreate(BaseModel):
    device_token: str

def _check_enabled():
    if not settings.mobile_foundation_enabled:
        raise HTTPException(status_code=403, detail="Mobile Foundation is disabled")

@router.post("/devices")
async def register_device(
    payload: DeviceCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = DeviceRegistry(session)
    device = await svc.register_device(
        client.id, client.id, payload.device_token, payload.platform, payload.model, payload.app_version
    )
    await session.commit()
    return device

@router.post("/sessions")
async def start_mobile_session(
    payload: SessionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    # 1. Verify device exists
    from sqlalchemy import select
    from app.models.mobile import MobileDevice
    stmt = select(MobileDevice).where(MobileDevice.device_token == payload.device_token)
    res = await session.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")

    # 2. Create session
    svc = MobileSessionService(session)
    mobile_session = await svc.create_session(client.id, client.id, device.id)
    await session.commit()
    return {
        "session_token": mobile_session.session_token,
        "expires_at": mobile_session.expires_at.isoformat()
    }

@router.get("/feed")
async def get_mobile_feed(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    # Return a mock feed of recent activities (agent runs, etc)
    from app.models.agents import AgentRun
    from sqlalchemy import select, desc
    stmt = select(AgentRun).where(AgentRun.tenant_id == client.id).order_by(desc(AgentRun.created_at)).limit(10)
    res = await session.execute(stmt)
    runs = res.scalars().all()
    
    return [
        {
            "id": str(run.id),
            "type": "agent_run",
            "title": f"Execução de Agente {run.agent_id}",
            "status": run.status,
            "timestamp": run.created_at.isoformat()
        }
        for run in runs
    ]

@router.post("/push/test")
async def test_push_notification(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    _check_enabled()
    svc = PushNotificationsService(session)
    await svc.send_push(
        client.id, client.id, "Teste de Push", "Esta é uma notificação de teste do LLM Stack"
    )
    await session.commit()
    return {"status": "sent_if_enabled"}
