from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
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
from app.models.billing_plan import BillingPlan
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
        clauses.append(column >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
    if end_date is not None:
        clauses.append(column < datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    return clauses


def _utc_day_window(reference: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(reference.date(), datetime.min.time(), tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _utc_month_window(reference: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(reference.date().replace(day=1), datetime.min.time(), tzinfo=timezone.utc)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, next_month


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
            "embeddings_requests": record.embeddings_requests,
            "embeddings_tokens": record.embeddings_tokens,
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


async def build_usage_by_client(session: AsyncSession) -> list[dict]:
    now = utc_now()
    today_start, tomorrow_start = _utc_day_window(now)
    month_start_dt, next_month_start = _utc_month_window(now)
    rows = (
        await session.execute(
            select(
                Client.id.label("client_id"),
                Client.name.label("client_name"),
                Client.billing_status.label("billing_status"),
                BillingPlan.code.label("billing_plan_code"),
                func.count(RequestLog.id).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start).label("requests_today"),
                func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start).label("requests_month"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("prompt_tokens_today"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("completion_tokens_today"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("prompt_tokens_month"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("completion_tokens_month"),
                func.coalesce(func.avg(RequestLog.latency_ms).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("avg_latency_ms_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(True)), 0).label("cache_hits_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(False)), 0).label("cache_misses_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.http_status >= 400), 0).label("errors_month"),
                func.max(RequestLog.created_at).label("last_request_at"),
            )
            .select_from(Client)
            .outerjoin(BillingPlan, BillingPlan.id == Client.billing_plan_id)
            .outerjoin(RequestLog, RequestLog.client_id == Client.id)
            .group_by(Client.id, Client.name, Client.billing_status, BillingPlan.code)
            .order_by(Client.created_at.desc())
        )
    ).mappings().all()
    payload = []
    for row in rows:
        requests_today = int(row["requests_today"] or 0)
        requests_month = int(row["requests_month"] or 0)
        prompt_today = int(row["prompt_tokens_today"] or 0)
        completion_today = int(row["completion_tokens_today"] or 0)
        prompt_month = int(row["prompt_tokens_month"] or 0)
        completion_month = int(row["completion_tokens_month"] or 0)
        cache_hits_month = int(row["cache_hits_month"] or 0)
        cache_misses_month = int(row["cache_misses_month"] or 0)
        total_today = prompt_today + completion_today
        total_month = prompt_month + completion_month
        payload.append(
            {
                "client_id": str(row["client_id"]),
                "client_name": row["client_name"],
                "name": row["client_name"],
                "billing_status": row["billing_status"],
                "billing_plan_code": row["billing_plan_code"],
                "requests_today": requests_today,
                "requests_month": requests_month,
                "requests_total": requests_month,
                "prompt_tokens_today": prompt_today,
                "completion_tokens_today": completion_today,
                "tokens_today": total_today,
                "prompt_tokens_month": prompt_month,
                "completion_tokens_month": completion_month,
                "tokens_month": total_month,
                "tokens_estimated_total": total_month,
                "avg_latency_ms_month": round(float(row["avg_latency_ms_month"] or 0), 2),
                "avg_latency_ms": round(float(row["avg_latency_ms_month"] or 0), 2),
                "cache_hits_month": cache_hits_month,
                "cache_misses_month": cache_misses_month,
                "cache_hit_rate_month": round(cache_hits_month / (cache_hits_month + cache_misses_month), 4) if (cache_hits_month + cache_misses_month) else 0.0,
                "errors_month": int(row["errors_month"] or 0),
                "errors_total": int(row["errors_month"] or 0),
                "estimated_cost_usd": 0.0,
                "last_request_at": _iso(row["last_request_at"]),
            }
        )
    return payload


async def build_usage_by_model(session: AsyncSession) -> list[dict]:
    now = utc_now()
    today_start, tomorrow_start = _utc_day_window(now)
    month_start_dt, next_month_start = _utc_month_window(now)
    rows = (
        await session.execute(
            select(
                RequestLog.model.label("model"),
                func.count(RequestLog.id).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start).label("requests_today"),
                func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start).label("requests_month"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("prompt_tokens_today"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("completion_tokens_today"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("prompt_tokens_month"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("completion_tokens_month"),
                func.coalesce(func.avg(RequestLog.latency_ms).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("avg_latency_ms_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.http_status >= 500), 0).label("backend_errors_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.http_status.between(400, 499)), 0).label("model_errors_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(True)), 0).label("cache_hits_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(False)), 0).label("cache_misses_month"),
            )
            .select_from(RequestLog)
            .group_by(RequestLog.model)
            .order_by(func.count(RequestLog.id).desc())
        )
    ).mappings().all()
    payload = []
    for row in rows:
        cache_hits_month = int(row["cache_hits_month"] or 0)
        cache_misses_month = int(row["cache_misses_month"] or 0)
        prompt_month = int(row["prompt_tokens_month"] or 0)
        completion_month = int(row["completion_tokens_month"] or 0)
        payload.append(
            {
                "model": row["model"],
                "requests_today": int(row["requests_today"] or 0),
                "requests_month": int(row["requests_month"] or 0),
                "prompt_tokens_today": int(row["prompt_tokens_today"] or 0),
                "completion_tokens_today": int(row["completion_tokens_today"] or 0),
                "tokens_today": int(row["prompt_tokens_today"] or 0) + int(row["completion_tokens_today"] or 0),
                "prompt_tokens_month": prompt_month,
                "completion_tokens_month": completion_month,
                "tokens_month": prompt_month + completion_month,
                "avg_latency_ms_month": round(float(row["avg_latency_ms_month"] or 0), 2),
                "backend_errors_month": int(row["backend_errors_month"] or 0),
                "model_errors_month": int(row["model_errors_month"] or 0),
                "cache_hits_month": cache_hits_month,
                "cache_misses_month": cache_misses_month,
                "cache_hit_rate_month": round(cache_hits_month / (cache_hits_month + cache_misses_month), 4) if (cache_hits_month + cache_misses_month) else 0.0,
            }
        )
    return payload


async def build_usage_summary(session: AsyncSession, *, queue_snapshot: dict | None = None) -> dict:
    now = utc_now()
    today_start, tomorrow_start = _utc_day_window(now)
    month_start_dt, next_month_start = _utc_month_window(now)
    request_totals = (
        await session.execute(
            select(
                func.count(RequestLog.id).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start).label("requests_today"),
                func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start).label("requests_month"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("prompt_tokens_today"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= today_start, RequestLog.created_at < tomorrow_start), 0).label("completion_tokens_today"),
                func.coalesce(func.sum(RequestLog.prompt_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("prompt_tokens_month"),
                func.coalesce(func.sum(RequestLog.completion_tokens_estimated).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("completion_tokens_month"),
                func.coalesce(func.avg(RequestLog.latency_ms).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start), 0).label("avg_latency_ms_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(True)), 0).label("cache_hits_month"),
                func.coalesce(func.count(RequestLog.id).filter(RequestLog.created_at >= month_start_dt, RequestLog.created_at < next_month_start, RequestLog.cache_hit.is_(False)), 0).label("cache_misses_month"),
            )
        )
    ).mappings().first() or {}
    invoice_totals = (
        await session.execute(
            select(
                func.count(BillingInvoice.id).label("invoices_total"),
                func.count().filter(BillingInvoice.status == "pending").label("invoices_pending"),
                func.count().filter(BillingInvoice.status == "paid").label("invoices_paid"),
                func.count().filter(BillingInvoice.status == "overdue").label("invoices_overdue"),
            )
        )
    ).mappings().first() or {}
    client_totals = (
        await session.execute(
            select(
                func.count(Client.id).label("clients_total"),
                func.count().filter(Client.billing_status == "active").label("clients_active"),
                func.count().filter(Client.billing_status == "suspended").label("clients_suspended"),
                func.count().filter(Client.is_blocked.is_(True)).label("clients_blocked"),
            )
        )
    ).mappings().first() or {}
    cache_hits_month = int(request_totals.get("cache_hits_month") or 0)
    cache_misses_month = int(request_totals.get("cache_misses_month") or 0)
    tokens_today = int(request_totals.get("prompt_tokens_today") or 0) + int(request_totals.get("completion_tokens_today") or 0)
    tokens_month = int(request_totals.get("prompt_tokens_month") or 0) + int(request_totals.get("completion_tokens_month") or 0)
    summary = {
        "generated_at": now.isoformat(),
        "requests_today": int(request_totals.get("requests_today") or 0),
        "requests_month": int(request_totals.get("requests_month") or 0),
        "prompt_tokens_today": int(request_totals.get("prompt_tokens_today") or 0),
        "completion_tokens_today": int(request_totals.get("completion_tokens_today") or 0),
        "tokens_today": tokens_today,
        "prompt_tokens_month": int(request_totals.get("prompt_tokens_month") or 0),
        "completion_tokens_month": int(request_totals.get("completion_tokens_month") or 0),
        "tokens_month": tokens_month,
        "avg_latency_ms_month": round(float(request_totals.get("avg_latency_ms_month") or 0), 2),
        "cache_hits_month": cache_hits_month,
        "cache_misses_month": cache_misses_month,
        "cache_hit_rate_month": round(cache_hits_month / (cache_hits_month + cache_misses_month), 4) if (cache_hits_month + cache_misses_month) else 0.0,
        "invoices_pending": int(invoice_totals.get("invoices_pending") or 0),
        "invoices_paid": int(invoice_totals.get("invoices_paid") or 0),
        "invoices_overdue": int(invoice_totals.get("invoices_overdue") or 0),
        "clients_active": int(client_totals.get("clients_active") or 0),
        "clients_suspended": int(client_totals.get("clients_suspended") or 0),
        "clients_blocked": int(client_totals.get("clients_blocked") or 0),
        "queues_by_plan": queue_snapshot or {},
    }
    summary["clients_total"] = int(client_totals.get("clients_total") or 0)
    summary["invoices_total"] = int(invoice_totals.get("invoices_total") or 0)
    return summary


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
                CustomerPayment.created_at >= datetime.combine(report_month, datetime.min.time(), tzinfo=timezone.utc),
                CustomerPayment.created_at < datetime.combine(next_month, datetime.min.time(), tzinfo=timezone.utc),
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
