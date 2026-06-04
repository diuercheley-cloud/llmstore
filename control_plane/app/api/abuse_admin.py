# Owner: platform-ops
import uuid

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.security import (
    acknowledge_action,
    get_abuse_summary,
    list_abuse_events,
    suspend_client,
    unsuspend_client,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/security/abuse",
    tags=["admin", "security", "abuse"],
    dependencies=[Depends(require_admin)],
)


@router.get("/events")
async def get_abuse_events(
    limit: int = Query(default=200, ge=1, le=1000),
    signal: str | None = Query(default=None),
    client_id: uuid.UUID | None = Query(default=None),
    severity: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    return await list_abuse_events(
        session,
        limit=limit,
        signal=signal,
        client_id=client_id,
        severity=severity,
    )


@router.get("/summary")
async def get_abuse_summary_endpoint(
    session: AsyncSession = Depends(get_db_session),
):
    return await get_abuse_summary(session)


@router.post("/actions/{action_id}/ack")
async def ack_action(
    action_id: uuid.UUID,
    acknowledged_by: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    result = await acknowledge_action(session, action_id, acknowledged_by)
    if result is None:
        raise HTTPException(status_code=404, detail="action not found")
    return result


@router.post("/clients/{client_id}/suspend")
async def admin_suspend_client(
    client_id: uuid.UUID,
    reason: str = Query(default="manual admin action"),
    session: AsyncSession = Depends(get_db_session),
):
    result = await suspend_client(session, client_id, reason)
    if result is None:
        raise HTTPException(status_code=404, detail="client not found")
    return result


@router.post("/clients/{client_id}/unsuspend")
async def admin_unsuspend_client(
    client_id: uuid.UUID,
    reason: str = Query(default="manual admin action"),
    session: AsyncSession = Depends(get_db_session),
):
    result = await unsuspend_client(session, client_id, reason)
    if result is None:
        raise HTTPException(status_code=404, detail="client not found")
    return result
