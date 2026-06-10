# Owner: platform-ops
import uuid
from datetime import date

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.export_reporting import (
    build_monthly_report,
    export_clients,
    export_invoices,
    export_payments,
    export_request_logs,
    export_security_events,
    export_usage,
    render_export_response,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin-exports"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _export_params(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    client_id: uuid.UUID | None = Query(default=None),
    format: str = Query(default="json", pattern="^(csv|json)$"),
):
    return {"start_date": start_date, "end_date": end_date, "client_id": client_id, "format": format}


@router.get("/export/clients")
async def export_clients_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_clients(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("clients", rows, params["format"])


@router.get("/export/usage")
async def export_usage_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_usage(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("usage", rows, params["format"])


@router.get("/export/invoices")
async def export_invoices_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_invoices(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("invoices", rows, params["format"])


@router.get("/export/payments")
async def export_payments_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_payments(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("payments", rows, params["format"])


@router.get("/export/security-events")
async def export_security_events_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_security_events(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("security-events", rows, params["format"])


@router.get("/export/request-logs")
async def export_request_logs_endpoint(
    params: dict = Depends(_export_params),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await export_request_logs(session, start_date=params["start_date"], end_date=params["end_date"], client_id=params["client_id"])
    return render_export_response("request-logs", rows, params["format"])


@router.get("/reports/monthly")
async def monthly_report(
    month: str | None = Query(default=None, description="YYYY-MM"),
    session: AsyncSession = Depends(get_db_session),
):
    return await build_monthly_report(session, month=month)
