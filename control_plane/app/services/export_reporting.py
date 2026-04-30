from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
import json
import uuid

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.customer_payment import CustomerPayment
from app.models.request_log import RequestLog
from app.models.security_event import SecurityEvent
from app.models.usage_record import UsageRecord
from app.services.billing import list_client_billing_snapshots, refresh_billing_statuses, resolve_effective_plan
from app.services.security_monitor import serialize_security_event


def _json_list(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _date_range_clause(column, start_date: date | None, end_date: date | None):
    clauses = []
    if start_date is not None:
        clauses.append(column >= start_date)
    if end_date is not None:
        clauses.append(column <= end_date)
    return clauses


def _datetime_range_clause(column, start_date: date | None, end_date: date | None):
    clauses = []
    if start_date is not None:
        clauses.append(column >= datetime.combine(start_date, datetime.min.time()))
    if end_date is not None:
        clauses.append(column < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    return clauses


def render_export_response(name: str, rows: list[dict], export_format: str):
    if export_format == "json":
        return JSONResponse(
            content={"exported_at": utc_now().isoformat(), "name": name, "rows": rows},
            headers={"Content-Disposition": f'attachment; filename="{name}.json"'},
        )
    output = StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=True) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
    )


async def export_clients(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    query = select(Client).order_by(Client.created_at.desc())
    clauses = _datetime_range_clause(Client.created_at, start_date, end_date)
    if client_id is not None:
        clauses.append(Client.id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).scalars().all()
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "is_blocked": item.is_blocked,
            "billing_status": item.billing_status,
            "billing_plan_id": str(item.billing_plan_id) if item.billing_plan_id else None,
            "rate_limit_per_minute": item.rate_limit_per_minute,
            "daily_token_quota": item.daily_token_quota,
            "monthly_token_quota": item.monthly_token_quota,
            "max_context_tokens": item.max_context_tokens,
            "max_output_tokens": item.max_output_tokens,
            "allowed_models": _json_list(item.allowed_models_json),
            "ip_allowlist": _json_list(item.ip_allowlist_json),
            "ip_blocklist": _json_list(item.ip_blocklist_json),
            "created_at": _iso(item.created_at),
            "updated_at": _iso(item.updated_at),
        }
        for item in rows
    ]


async def export_usage(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    query = (
        select(UsageRecord, Client.name.label("client_name"))
        .join(Client, Client.id == UsageRecord.client_id)
        .order_by(UsageRecord.period_start.desc(), UsageRecord.created_at.desc())
    )
    clauses = _date_range_clause(UsageRecord.period_start, start_date, end_date)
    if client_id is not None:
        clauses.append(UsageRecord.client_id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).all()
    return [
        {
            "id": str(record.id),
            "client_id": str(record.client_id),
            "client_name": client_name,
            "period_start": _iso(record.period_start),
            "period_type": record.period_type,
            "request_count": record.request_count,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.prompt_tokens + record.completion_tokens,
            "created_at": _iso(record.created_at),
            "updated_at": _iso(record.updated_at),
        }
        for record, client_name in rows
    ]


async def export_invoices(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    await refresh_billing_statuses(session)
    query = (
        select(BillingInvoice, Client.name.label("client_name"))
        .join(Client, Client.id == BillingInvoice.client_id)
        .order_by(BillingInvoice.created_at.desc())
    )
    clauses = _datetime_range_clause(BillingInvoice.created_at, start_date, end_date)
    if client_id is not None:
        clauses.append(BillingInvoice.client_id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).all()
    return [
        {
            "id": str(invoice.id),
            "client_id": str(invoice.client_id),
            "client_name": client_name,
            "billing_plan_id": str(invoice.billing_plan_id) if invoice.billing_plan_id else None,
            "status": invoice.status,
            "currency": invoice.currency,
            "period_start": _iso(invoice.period_start),
            "period_end": _iso(invoice.period_end),
            "monthly_price": float(invoice.monthly_price),
            "included_tokens": invoice.included_tokens,
            "used_tokens": invoice.used_tokens,
            "overage_tokens": invoice.overage_tokens,
            "overage_price_per_1k_tokens": float(invoice.overage_price_per_1k_tokens),
            "overage_cost": float(invoice.overage_cost),
            "total_amount": float(invoice.total_amount),
            "payment_method": invoice.payment_method,
            "due_at": _iso(invoice.due_at),
            "paid_at": _iso(invoice.paid_at),
            "cancelled_at": _iso(invoice.cancelled_at),
            "created_at": _iso(invoice.created_at),
            "updated_at": _iso(invoice.updated_at),
        }
        for invoice, client_name in rows
    ]


async def export_payments(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    query = (
        select(CustomerPayment, Client.name.label("client_name"))
        .join(Client, Client.id == CustomerPayment.client_id)
        .order_by(CustomerPayment.created_at.desc())
    )
    clauses = _datetime_range_clause(CustomerPayment.created_at, start_date, end_date)
    if client_id is not None:
        clauses.append(CustomerPayment.client_id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).all()
    return [
        {
            "id": str(payment.id),
            "invoice_id": str(payment.invoice_id),
            "client_id": str(payment.client_id),
            "client_name": client_name,
            "status": payment.status,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_reference": payment.payment_reference,
            "note": payment.note,
            "paid_at": _iso(payment.paid_at),
            "cancelled_at": _iso(payment.cancelled_at),
            "created_at": _iso(payment.created_at),
            "updated_at": _iso(payment.updated_at),
        }
        for payment, client_name in rows
    ]


async def export_security_events(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    query = select(SecurityEvent).order_by(SecurityEvent.created_at.desc())
    clauses = _datetime_range_clause(SecurityEvent.created_at, start_date, end_date)
    if client_id is not None:
        clauses.append(SecurityEvent.client_id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).scalars().all()
    return [serialize_security_event(row) for row in rows]


async def export_request_logs(session: AsyncSession, *, start_date: date | None, end_date: date | None, client_id: uuid.UUID | None) -> list[dict]:
    query = select(RequestLog).order_by(RequestLog.created_at.desc())
    clauses = _datetime_range_clause(RequestLog.created_at, start_date, end_date)
    if client_id is not None:
        clauses.append(RequestLog.client_id == client_id)
    if clauses:
        query = query.where(and_(*clauses))
    rows = (await session.execute(query)).scalars().all()
    return [
        {
            "id": str(row.id),
            "client_id": str(row.client_id),
            "model": row.model,
            "endpoint": row.endpoint,
            "prompt_tokens_estimated": row.prompt_tokens_estimated,
            "completion_tokens_estimated": row.completion_tokens_estimated,
            "latency_ms": row.latency_ms,
            "http_status": row.http_status,
            "is_stream": row.is_stream,
            "estimated_cost_usd": float(row.estimated_cost_usd or 0),
            "backend_name": row.backend_name,
            "attempts": row.attempts,
            "fallback_used": row.fallback_used,
            "cache_hit": row.cache_hit,
            "backend_errors": _json_list(row.backend_errors_json),
            "error_message": row.error_message,
            "request_summary": row.request_summary,
            "correlation_id": row.correlation_id,
            "source_ip": row.source_ip,
            "created_at": _iso(row.created_at),
        }
        for row in rows
    ]


async def build_monthly_report(session: AsyncSession, *, month: str | None = None) -> dict:
    if month:
        try:
            report_month = date.fromisoformat(f"{month}-01")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="month must use YYYY-MM format") from exc
    else:
        today = date.today()
        report_month = today.replace(day=1)
    next_month = (report_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_end = next_month - timedelta(days=1)

    invoices = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.client))
            .where(BillingInvoice.period_start == report_month)
        )
    ).scalars().all()
    payments = (
        await session.execute(
            select(CustomerPayment).where(
                CustomerPayment.created_at >= datetime.combine(report_month, datetime.min.time()),
                CustomerPayment.created_at < datetime.combine(next_month, datetime.min.time()),
            )
        )
    ).scalars().all()
    active_clients = int(
        (
            await session.execute(
                select(func.count(Client.id)).where(Client.is_blocked.is_(False), Client.billing_status == "active")
            )
        ).scalar_one()
        or 0
    )
    usage_rows = (
        await session.execute(
            select(UsageRecord).where(
                UsageRecord.period_type == "monthly",
                UsageRecord.period_start == report_month,
            )
        )
    ).scalars().all()

    snapshots = await list_client_billing_snapshots(session, usage_reference_date=report_month)
    forecast_revenue = round(sum(float(item["invoice_preview"]["total_estimated"]) for item in snapshots), 6)
    paid_revenue = round(sum(float(payment.amount) for payment in payments if payment.status == "paid"), 6)
    overdue_revenue = round(sum(float(invoice.total_amount) for invoice in invoices if invoice.status in {"pending", "overdue"}), 6)
    consumed_tokens = sum(int(row.prompt_tokens + row.completion_tokens) for row in usage_rows)
    estimated_cost = round((Decimal(consumed_tokens) / Decimal(1000) * Decimal("0.010000")), 6) if consumed_tokens else Decimal("0.000000")
    estimated_margin = round(Decimal(str(forecast_revenue)) - estimated_cost, 6)
    return {
        "month": report_month.strftime("%Y-%m"),
        "period_start": report_month.isoformat(),
        "period_end": period_end.isoformat(),
        "forecast_revenue_usd": forecast_revenue,
        "paid_revenue_usd": paid_revenue,
        "delinquency_usd": overdue_revenue,
        "active_clients": active_clients,
        "consumed_tokens": consumed_tokens,
        "estimated_cost_usd": float(estimated_cost),
        "estimated_margin_usd": float(estimated_margin),
        "invoices_total": len(invoices),
        "payments_total": len(payments),
    }
