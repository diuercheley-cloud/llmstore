# Owner: platform-ops
# Owner: platform-ops

from app.api.dependencies.auth import get_current_admin
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.core.managed_control_plane import ManagedControlPlaneLink
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/managed-control-plane", tags=["managed_control_plane_admin"])

@router.post("/link")
async def link_control_plane(upstream_url: str, db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    link = ManagedControlPlaneLink(upstream_url=upstream_url, status="linked", last_heartbeat_at=utc_now())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link

@router.get("/heartbeat")
async def get_heartbeat(db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    return {"status": "ok"}
