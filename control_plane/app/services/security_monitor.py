from __future__ import annotations

from datetime import datetime
import hashlib
import json
import logging
import uuid

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import BILLING_STATUS_GAUGE, SECURITY_EVENT_COUNTER
from app.core.request_context import get_correlation_id, get_source_ip
from app.core.time import utc_now
from app.models.client import Client
from app.models.request_log import RequestLog
from app.models.security_event import SecurityEvent

logger = logging.getLogger(__name__)

INVALID_API_ATTEMPT_THRESHOLD = 5
REQUEST_ERROR_THRESHOLD = 5
LARGE_PROMPT_TOKENS = 2048
REPEATED_PROMPT_THRESHOLD = 3
PLAN_USAGE_THRESHOLD = 0.9


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def serialize_security_event(event: SecurityEvent) -> dict:
    details = {}
    if event.detail_json:
        try:
            details = json.loads(event.detail_json)
        except json.JSONDecodeError:
            details = {"raw": event.detail_json}
    return {
        "id": str(event.id),
        "client_id": str(event.client_id) if event.client_id else None,
        "request_log_id": str(event.request_log_id) if event.request_log_id else None,
        "event_type": event.event_type,
        "severity": event.severity,
        "correlation_id": event.correlation_id,
        "source_ip": event.source_ip,
        "api_key_prefix": event.api_key_prefix,
        "title": event.title,
        "details": details,
        "created_at": event.created_at.isoformat(),
    }


async def log_security_event(
    session: AsyncSession,
    *,
    event_type: str,
    severity: str,
    title: str,
    client_id=None,
    request_log_id=None,
    correlation_id: str | None = None,
    source_ip: str | None = None,
    api_key_prefix: str | None = None,
    details: dict | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        client_id=client_id,
        request_log_id=request_log_id,
        event_type=event_type,
        severity=severity,
        correlation_id=correlation_id or get_correlation_id() or None,
        source_ip=source_ip or get_source_ip() or None,
        api_key_prefix=api_key_prefix,
        title=title,
        detail_json=json.dumps(details, ensure_ascii=True) if details else None,
        created_at=utc_now(),
    )
    session.add(event)
    SECURITY_EVENT_COUNTER.labels(event_type=event_type, severity=severity).inc()
    logger.warning(
        "security event recorded",
        extra={"extra_data": {"event_type": event_type, "severity": severity, "client_id": str(client_id) if client_id else None}},
    )
    return event


def prompt_fingerprint(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def enforce_client_ip_policy(session: AsyncSession, client: Client, source_ip: str) -> None:
    allowlist = _parse_json_list(client.ip_allowlist_json)
    blocklist = _parse_json_list(client.ip_blocklist_json)
    if source_ip in blocklist:
        await log_security_event(
            session,
            event_type="ip_blocklist_match",
            severity="high",
            title="Request from blocked IP",
            client_id=client.id,
            details={"source_ip": source_ip},
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="source ip is blocked for this client")
    if allowlist and source_ip not in allowlist:
        await log_security_event(
            session,
            event_type="ip_allowlist_miss",
            severity="high",
            title="Request outside allowlist",
            client_id=client.id,
            details={"source_ip": source_ip, "allowlist_size": len(allowlist)},
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="source ip is not allowed for this client")


async def record_invalid_api_key_attempt(
    session: AsyncSession,
    redis: Redis,
    *,
    source_ip: str,
    api_key_prefix: str | None,
    reason: str,
) -> None:
    key = f"security:invalid-api-key:{source_ip}:{api_key_prefix or 'missing'}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, 600)
    if attempts >= INVALID_API_ATTEMPT_THRESHOLD:
        gate = f"{key}:event:{attempts}"
        if await redis.set(gate, "1", ex=600, nx=True):
            await log_security_event(
                session,
                event_type="invalid_api_key_attempts",
                severity="high",
                title="Many invalid API key attempts",
                source_ip=source_ip,
                api_key_prefix=api_key_prefix,
                details={"attempts": attempts, "window_seconds": 600, "reason": reason},
            )
            await session.commit()


async def maybe_record_repeated_large_prompt(
    session: AsyncSession,
    redis: Redis,
    *,
    client: Client,
    prompt_tokens: int,
    prompt_key: str,
    endpoint: str,
) -> None:
    if prompt_tokens < LARGE_PROMPT_TOKENS:
        return
    key = f"security:prompt-repeat:{client.id}:{prompt_key}"
    seen = await redis.incr(key)
    if seen == 1:
        await redis.expire(key, 900)
    if seen >= REPEATED_PROMPT_THRESHOLD:
        gate = f"{key}:event:{seen}"
        if await redis.set(gate, "1", ex=900, nx=True):
            await log_security_event(
                session,
                event_type="repeated_large_prompt",
                severity="medium",
                title="Large prompt repeated multiple times",
                client_id=client.id,
                details={"endpoint": endpoint, "prompt_tokens": prompt_tokens, "repetitions": seen},
            )


async def maybe_record_plan_usage_anomaly(
    session: AsyncSession,
    *,
    client: Client,
    daily_limit: int,
    weekly_limit: int,
    monthly_limit: int,
    incoming_tokens: int,
    daily_used_before: int,
    weekly_used_before: int,
    monthly_used_before: int,
) -> None:
    daily_ratio = (daily_used_before + incoming_tokens) / daily_limit if daily_limit else 0
    weekly_ratio = (weekly_used_before + incoming_tokens) / weekly_limit if weekly_limit else 0
    monthly_ratio = (monthly_used_before + incoming_tokens) / monthly_limit if monthly_limit else 0
    if max(daily_ratio, weekly_ratio, monthly_ratio) < PLAN_USAGE_THRESHOLD:
        return
    await log_security_event(
        session,
        event_type="usage_above_plan_pattern",
        severity="medium",
        title="Usage pattern above expected plan threshold",
        client_id=client.id,
        details={
            "incoming_tokens": incoming_tokens,
            "daily_ratio": round(daily_ratio, 4),
            "weekly_ratio": round(weekly_ratio, 4),
            "monthly_ratio": round(monthly_ratio, 4),
        },
    )


async def maybe_record_request_error_burst(
    session: AsyncSession,
    redis: Redis,
    *,
    client_id,
    endpoint: str,
    status_code: int,
    backend_name: str | None,
) -> None:
    if status_code < 400:
        return
    key = f"security:error-burst:{client_id}:{status_code // 100}"
    total = await redis.incr(key)
    if total == 1:
        await redis.expire(key, 900)
    if total >= REQUEST_ERROR_THRESHOLD:
        gate = f"{key}:event:{total}"
        if await redis.set(gate, "1", ex=900, nx=True):
            await log_security_event(
                session,
                event_type="request_error_burst",
                severity="high" if status_code >= 500 else "medium",
                title="Many request errors for client",
                client_id=client_id,
                details={"endpoint": endpoint, "status_code": status_code, "count": total, "backend_name": backend_name},
            )


async def list_security_events(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(SecurityEvent).order_by(desc(SecurityEvent.created_at)).limit(500))).scalars().all()
    return [serialize_security_event(row) for row in rows]


async def observe_billing_status_metrics(session: AsyncSession) -> None:
    rows = (
        await session.execute(
            select(Client.billing_status, func.count(Client.id)).group_by(Client.billing_status)
        )
    ).all()
    for status_name in ("active", "past_due", "suspended"):
        BILLING_STATUS_GAUGE.labels(billing_status=status_name).set(0)
    for status_name, total in rows:
        BILLING_STATUS_GAUGE.labels(billing_status=str(status_name)).set(int(total or 0))


async def suspend_client_for_security(session: AsyncSession, client: Client, reason: str) -> None:
    client.is_blocked = True
    metadata = {}
    if client.metadata_json:
        try:
            metadata = json.loads(client.metadata_json)
        except json.JSONDecodeError:
            metadata = {"raw_metadata": client.metadata_json}
    metadata["security_suspension_reason"] = reason
    metadata["security_suspended_at"] = utc_now().isoformat()
    client.metadata_json = json.dumps(metadata, ensure_ascii=True)
    client.updated_at = utc_now()
    await log_security_event(
        session,
        event_type="client_suspended",
        severity="high",
        title="Client suspended by security action",
        client_id=client.id,
        details={"reason": reason},
    )


async def unsuspend_client_for_security(session: AsyncSession, client: Client) -> None:
    client.is_blocked = False
    metadata = {}
    if client.metadata_json:
        try:
            metadata = json.loads(client.metadata_json)
        except json.JSONDecodeError:
            metadata = {"raw_metadata": client.metadata_json}
    metadata.pop("security_suspension_reason", None)
    metadata["security_unsuspended_at"] = utc_now().isoformat()
    client.metadata_json = json.dumps(metadata, ensure_ascii=True)
    client.updated_at = utc_now()
    await log_security_event(
        session,
        event_type="client_unsuspended",
        severity="medium",
        title="Client unsuspended by security action",
        client_id=client.id,
    )
