from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_billing_dispute import CommercialBillingDispute
from app.models.commercial.commercial_financial_anomaly import CommercialFinancialAnomaly
from app.models.commercial.commercial_financial_reconciliation import CommercialFinancialReconciliation
from app.models.commercial.commercial_revenue_alert_delivery import CommercialRevenueAlertDelivery
from app.models.commercial.commercial_revenue_escalation_policy import CommercialRevenueEscalationPolicy
from app.models.commercial.commercial_revenue_protection_action import CommercialRevenueProtectionAction
from app.services.routing.commercial_report_email import (
    EmailAttachment,
    build_email_message,
    send_report_email,
    send_report_email_dry_run,
    validate_recipient_allowlist,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
VALID_SOURCE_TYPES = {"anomaly", "policy_action", "forecast", "reconciliation", "dispute"}
VALID_DELIVERY_TYPES = ("webhook", "slack", "pagerduty", "email")
SENSITIVE_KEYWORDS = {
    "api_key",
    "authorization",
    "secret",
    "token",
    "password",
    "prompt",
    "response",
    "responses",
    "payload",
    "routing_key",
    "webhook_url",
    "smtp_password",
}
SENSITIVE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]{8,}", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|secret|token|password|routing_key)\b\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]


def _json_default(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _hash_payload(payload: dict[str, Any]) -> str:
    stable_payload = {key: value for key, value in payload.items() if key != "timestamp"}
    serialized = json.dumps(stable_payload, sort_keys=True, ensure_ascii=True, default=_json_default)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _safe_string(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    sanitized = sanitize_alert_payload(value)
    if isinstance(sanitized, (dict, list)):
        return json.dumps(sanitized, sort_keys=True, ensure_ascii=True, default=_json_default)[:limit]
    return str(sanitized)[:limit]


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_now().tzinfo)
    return value


def _mask_url(url: str | None) -> str:
    if not url:
        return "not_configured"
    match = re.match(r"^(https?://)([^/]+)(/.*)?$", url.strip())
    if not match:
        return "***"
    scheme, host, path = match.groups()
    host_parts = host.split(".")
    masked_host = host_parts[0][:1] + "***"
    if len(host_parts) > 1:
        masked_host = ".".join([masked_host, *host_parts[1:]])
    suffix = "..." if path else ""
    return f"{scheme}{masked_host}{suffix}"


def _mask_token(token: str | None) -> str:
    if not token:
        return "not_configured"
    token = token.strip()
    if len(token) <= 6:
        return "***"
    return f"{token[:2]}***{token[-2:]}"


def _mask_email(recipient: str) -> str:
    local, _, domain = recipient.partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def _destination_for(delivery_type: str) -> str:
    settings = get_settings()
    if delivery_type == "webhook":
        return _mask_url(settings.commercial_revenue_webhook_url)
    if delivery_type == "slack":
        return _mask_url(settings.commercial_revenue_slack_webhook_url)
    if delivery_type == "pagerduty":
        return _mask_token(settings.commercial_revenue_pagerduty_routing_key)
    recipients = [item.strip().lower() for item in settings.commercial_revenue_email_escalation_recipients.split(",") if item.strip()]
    return ", ".join(_mask_email(item) for item in recipients) if recipients else "not_configured"


def sanitize_alert_payload(payload: Any) -> Any:
    def _walk(node: Any, parent_key: str = "value") -> Any:
        key = parent_key.lower()
        if any(secret_key in key for secret_key in SENSITIVE_KEYWORDS):
            return "[REDACTED]"
        if isinstance(node, dict):
            return {str(k): _walk(v, str(k)) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(item, parent_key) for item in node]
        if isinstance(node, str):
            value = node
            for pattern in SENSITIVE_PATTERNS:
                value = pattern.sub("[REDACTED]", value)
            return value[:2000]
        if isinstance(node, (uuid.UUID, datetime)):
            return _json_default(node)
        return node

    return _walk(payload)


def build_alert_payload(
    *,
    source_type: str,
    source_id: str,
    severity: str,
    summary: str,
    recommendation: str | None = None,
    timestamp: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    trigger_type: str | None = None,
) -> dict[str, Any]:
    payload = {
        "source_type": source_type,
        "source_id": str(source_id),
        "trigger_type": trigger_type or source_type,
        "severity": severity,
        "summary": summary,
        "recommendation": recommendation or "Investigate and validate the revenue control path.",
        "timestamp": (timestamp or utc_now()).isoformat(),
        "metadata": metadata or {},
    }
    return sanitize_alert_payload(payload)


def apply_retry_backoff(retry_count: int, *, base_seconds: int = 30, max_seconds: int = 1800) -> int:
    retry_count = max(0, retry_count)
    return min(max_seconds, max(1, base_seconds) * (2 ** retry_count))


async def dedupe_alert(
    session: AsyncSession,
    *,
    dedupe_key: str,
    delivery_type: str,
    payload_hash: str,
    cooldown_minutes: int,
) -> str | None:
    stmt = (
        select(CommercialRevenueAlertDelivery)
        .where(
            CommercialRevenueAlertDelivery.dedupe_key == dedupe_key,
            CommercialRevenueAlertDelivery.delivery_type == delivery_type,
        )
        .order_by(desc(CommercialRevenueAlertDelivery.created_at))
        .limit(1)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        return None
    if existing.payload_hash == payload_hash and existing.status in {"dry_run", "sent", "pending", "deduplicated"}:
        return "deduplicated"
    existing_created_at = _normalize_dt(existing.created_at)
    if cooldown_minutes > 0 and existing_created_at and existing_created_at >= utc_now() - timedelta(minutes=cooldown_minutes):
        return "suppressed"
    return None


async def _post_json(
    url: str,
    *,
    json_payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    max_retries: int,
) -> tuple[int, str]:
    last_error: str | None = None
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=json_payload, headers=headers or {})
            return response.status_code, _safe_string({"status_code": response.status_code, "body": response.text[:300]}) or ""
        except httpx.HTTPError as exc:
            last_error = _safe_string(str(exc)) or "http_error"
            if attempt >= max_retries:
                break
            await asyncio.sleep(apply_retry_backoff(attempt, base_seconds=1, max_seconds=4))
    raise RuntimeError(last_error or "delivery_failed")


async def deliver_webhook(payload: dict[str, Any], *, max_retries: int) -> dict[str, Any]:
    settings = get_settings()
    timestamp = str(int(utc_now().timestamp()))
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=_json_default)
    signature = hmac.new(
        settings.commercial_revenue_webhook_signing_secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Commercial-Revenue-Timestamp": timestamp,
        "X-Commercial-Revenue-Signature": f"v1={signature}",
    }
    status_code, summary = await _post_json(
        settings.commercial_revenue_webhook_url,
        json_payload=payload,
        headers=headers,
        max_retries=max_retries,
    )
    return {"status": "sent", "response_code": status_code, "response_summary": summary}


async def deliver_slack(payload: dict[str, Any], *, max_retries: int) -> dict[str, Any]:
    settings = get_settings()
    slack_payload = {
        "text": f"[{payload['severity'].upper()}] {payload['source_type']}: {payload['summary']}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Severity:* {payload['severity']}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Source:* {payload['source_type']}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:* {payload['summary']}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Recommendation:* {payload['recommendation']}"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": payload["timestamp"]}]},
        ],
    }
    status_code, summary = await _post_json(
        settings.commercial_revenue_slack_webhook_url,
        json_payload=slack_payload,
        max_retries=max_retries,
    )
    return {"status": "sent", "response_code": status_code, "response_summary": summary}


async def deliver_pagerduty(payload: dict[str, Any], *, dedupe_key: str, max_retries: int) -> dict[str, Any]:
    settings = get_settings()
    pd_payload = {
        "routing_key": settings.commercial_revenue_pagerduty_routing_key,
        "event_action": "trigger",
        "dedup_key": dedupe_key,
        "payload": {
            "summary": payload["summary"],
            "severity": payload["severity"],
            "source": "llm-inference-stack",
            "timestamp": payload["timestamp"],
        },
    }
    status_code, summary = await _post_json(
        "https://events.pagerduty.com/v2/enqueue",
        json_payload=pd_payload,
        max_retries=max_retries,
    )
    return {"status": "sent", "response_code": status_code, "response_summary": summary}


async def deliver_email(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    recipients = [item.strip().lower() for item in settings.commercial_revenue_email_escalation_recipients.split(",") if item.strip()]
    validate_recipient_allowlist(recipients, settings=settings)
    subject = f"[Revenue Escalation][{payload['severity'].upper()}] {payload['source_type']}"
    body = (
        f"Severity: {payload['severity']}\n"
        f"Source Type: {payload['source_type']}\n"
        f"Summary: {payload['summary']}\n"
        f"Recommendation: {payload['recommendation']}\n"
        f"Timestamp: {payload['timestamp']}\n"
    )
    message = build_email_message(
        subject=subject,
        recipients=recipients,
        body_text=body,
        attachments=[EmailAttachment(filename="revenue-escalation.json", content=json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8"), mime_type="application/json")],
        settings=settings,
    )
    result = send_report_email(message, recipients, settings=settings)
    return {"status": "sent", "response_code": 250, "response_summary": _safe_string(result)}


def _channel_enabled(delivery_type: str) -> bool:
    settings = get_settings()
    if delivery_type == "webhook":
        return (
            settings.commercial_revenue_webhook_enabled
            and bool(settings.commercial_revenue_webhook_url.strip())
            and bool(settings.commercial_revenue_webhook_signing_secret.strip())
        )
    if delivery_type == "slack":
        return settings.commercial_revenue_slack_enabled and bool(settings.commercial_revenue_slack_webhook_url.strip())
    if delivery_type == "pagerduty":
        return settings.commercial_revenue_pagerduty_enabled and bool(settings.commercial_revenue_pagerduty_routing_key.strip())
    if delivery_type == "email":
        return settings.commercial_revenue_email_escalation_enabled and bool(settings.commercial_revenue_email_escalation_recipients.strip())
    return False


def _policy_matches(policy: CommercialRevenueEscalationPolicy, *, source_type: str, trigger_type: str, severity: str) -> bool:
    if not policy.enabled:
        return False
    if SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER.get(policy.severity_threshold, 0):
        return False
    triggers = [str(item).strip() for item in (policy.trigger_types_json or []) if str(item).strip()]
    if not triggers:
        return True
    return "*" in triggers or source_type in triggers or trigger_type in triggers


async def _record_delivery(
    session: AsyncSession,
    *,
    source_type: str,
    source_id: str,
    severity: str,
    delivery_type: str,
    destination: str,
    status: str,
    dedupe_key: str,
    payload_hash: str,
    retry_count: int = 0,
    response_code: int | None = None,
    response_summary: str | None = None,
    delivered_at: datetime | None = None,
) -> CommercialRevenueAlertDelivery:
    row = CommercialRevenueAlertDelivery(
        source_type=source_type,
        source_id=str(source_id),
        severity=severity,
        delivery_type=delivery_type,
        destination=destination,
        status=status,
        dedupe_key=dedupe_key,
        retry_count=retry_count,
        response_code=response_code,
        response_summary=response_summary,
        payload_hash=payload_hash,
        delivered_at=delivered_at,
    )
    session.add(row)
    await session.flush()
    return row


async def _deliver_one(
    session: AsyncSession,
    *,
    source_type: str,
    source_id: str,
    severity: str,
    delivery_type: str,
    payload: dict[str, Any],
    cooldown_minutes: int,
    max_retries: int,
) -> CommercialRevenueAlertDelivery:
    settings = get_settings()
    destination = _destination_for(delivery_type)
    dedupe_key = hashlib.sha256(f"{source_type}:{source_id}:{severity}:{delivery_type}:{payload.get('trigger_type')}".encode("utf-8")).hexdigest()
    payload_hash = _hash_payload(payload)
    dedupe_state = await dedupe_alert(
        session,
        dedupe_key=dedupe_key,
        delivery_type=delivery_type,
        payload_hash=payload_hash,
        cooldown_minutes=cooldown_minutes,
    )
    if dedupe_state:
        return await _record_delivery(
            session,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            delivery_type=delivery_type,
            destination=destination,
            status=dedupe_state,
            dedupe_key=dedupe_key,
            payload_hash=payload_hash,
            response_summary=dedupe_state,
        )

    if settings.commercial_revenue_escalations_mode == "disabled":
        return await _record_delivery(
            session,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            delivery_type=delivery_type,
            destination=destination,
            status="suppressed",
            dedupe_key=dedupe_key,
            payload_hash=payload_hash,
            response_summary="escalations_disabled",
        )

    if not _channel_enabled(delivery_type):
        return await _record_delivery(
            session,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            delivery_type=delivery_type,
            destination=destination,
            status="suppressed",
            dedupe_key=dedupe_key,
            payload_hash=payload_hash,
            response_summary="channel_disabled",
        )

    if settings.commercial_revenue_escalations_mode == "dry_run":
        try:
            if delivery_type == "email":
                dry_run_result = send_report_email_dry_run(
                    subject=f"[Revenue Escalation][{severity.upper()}] {source_type}",
                    recipients=[item.strip().lower() for item in settings.commercial_revenue_email_escalation_recipients.split(",") if item.strip()],
                    attachments=[EmailAttachment(filename="revenue-escalation.json", content=json.dumps(payload, ensure_ascii=True).encode("utf-8"), mime_type="application/json")],
                    settings=settings,
                )
                response_summary = _safe_string(dry_run_result)
            else:
                response_summary = "dry_run"
            return await _record_delivery(
                session,
                source_type=source_type,
                source_id=source_id,
                severity=severity,
                delivery_type=delivery_type,
                destination=destination,
                status="dry_run",
                dedupe_key=dedupe_key,
                payload_hash=payload_hash,
                response_summary=response_summary,
                delivered_at=utc_now(),
            )
        except Exception as exc:
            return await _record_delivery(
                session,
                source_type=source_type,
                source_id=source_id,
                severity=severity,
                delivery_type=delivery_type,
                destination=destination,
                status="failed",
                dedupe_key=dedupe_key,
                payload_hash=payload_hash,
                response_summary=_safe_string(str(exc)),
            )

    try:
        if delivery_type == "webhook":
            result = await deliver_webhook(payload, max_retries=max_retries)
        elif delivery_type == "slack":
            result = await deliver_slack(payload, max_retries=max_retries)
        elif delivery_type == "pagerduty":
            result = await deliver_pagerduty(payload, dedupe_key=dedupe_key, max_retries=max_retries)
        else:
            result = await deliver_email(payload)
        return await _record_delivery(
            session,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            delivery_type=delivery_type,
            destination=destination,
            status="sent",
            dedupe_key=dedupe_key,
            payload_hash=payload_hash,
            response_code=result.get("response_code"),
            response_summary=_safe_string(result.get("response_summary") or result),
            delivered_at=utc_now(),
        )
    except Exception as exc:
        return await _record_delivery(
            session,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            delivery_type=delivery_type,
            destination=destination,
            status="failed",
            dedupe_key=dedupe_key,
            payload_hash=payload_hash,
            response_summary=_safe_string(str(exc)),
        )


async def evaluate_escalation_policies(
    session: AsyncSession,
    *,
    source_type: str,
    source_id: str | uuid.UUID,
    severity: str,
    summary: str,
    recommendation: str | None = None,
    metadata: dict[str, Any] | None = None,
    trigger_type: str | None = None,
    timestamp: datetime | None = None,
    delivery_types: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    normalized_source_type = source_type if source_type in VALID_SOURCE_TYPES else "policy_action"
    normalized_trigger_type = (trigger_type or normalized_source_type).strip()
    payload = build_alert_payload(
        source_type=normalized_source_type,
        source_id=str(source_id),
        severity=severity,
        summary=summary,
        recommendation=recommendation,
        timestamp=timestamp,
        metadata=metadata,
        trigger_type=normalized_trigger_type,
    )
    if not settings.commercial_revenue_escalations_enabled:
        return {"enabled": False, "deliveries": [], "payload": payload}

    policies = (
        await session.execute(
            select(CommercialRevenueEscalationPolicy)
            .where(CommercialRevenueEscalationPolicy.enabled.is_(True))
            .order_by(desc(CommercialRevenueEscalationPolicy.created_at))
        )
    ).scalars().all()
    deliveries: list[CommercialRevenueAlertDelivery] = []
    matched_policy_ids: list[str] = []

    for policy in policies:
        if not _policy_matches(policy, source_type=normalized_source_type, trigger_type=normalized_trigger_type, severity=severity):
            continue
        matched_policy_ids.append(str(policy.id))
        allowed = [item for item in (policy.allowed_delivery_types_json or list(VALID_DELIVERY_TYPES)) if item in VALID_DELIVERY_TYPES]
        ordered = [item for item in (policy.escalation_order_json or allowed) if item in allowed]
        types_to_process = [item for item in ordered if not delivery_types or item in delivery_types]
        for delivery_type in types_to_process:
            delivery = await _deliver_one(
                session,
                source_type=normalized_source_type,
                source_id=str(source_id),
                severity=severity,
                delivery_type=delivery_type,
                payload=payload,
                cooldown_minutes=policy.cooldown_minutes or settings.commercial_revenue_escalation_cooldown_minutes,
                max_retries=max(policy.max_retries, 0),
            )
            deliveries.append(delivery)

    await session.commit()
    return {
        "enabled": True,
        "mode": settings.commercial_revenue_escalations_mode,
        "matched_policies": matched_policy_ids,
        "deliveries": [
            {
                "id": str(item.id),
                "delivery_type": item.delivery_type,
                "status": item.status,
                "destination": item.destination,
                "retry_count": item.retry_count,
            }
            for item in deliveries
        ],
        "payload": payload,
    }


async def summarize_deliveries(session: AsyncSession) -> dict[str, Any]:
    deliveries = (
        await session.execute(
            select(CommercialRevenueAlertDelivery)
            .order_by(desc(CommercialRevenueAlertDelivery.created_at))
            .limit(100)
        )
    ).scalars().all()
    policies = (
        await session.execute(
            select(CommercialRevenueEscalationPolicy)
            .order_by(desc(CommercialRevenueEscalationPolicy.created_at))
            .limit(50)
        )
    ).scalars().all()
    by_status = {
        status: count
        for status, count in (
            await session.execute(
                select(CommercialRevenueAlertDelivery.status, func.count(CommercialRevenueAlertDelivery.id))
                .group_by(CommercialRevenueAlertDelivery.status)
            )
        ).all()
    }
    by_delivery_type = {
        delivery_type: count
        for delivery_type, count in (
            await session.execute(
                select(CommercialRevenueAlertDelivery.delivery_type, func.count(CommercialRevenueAlertDelivery.id))
                .group_by(CommercialRevenueAlertDelivery.delivery_type)
            )
        ).all()
    }
    return {
        "enabled": get_settings().commercial_revenue_escalations_enabled,
        "mode": get_settings().commercial_revenue_escalations_mode,
        "cooldown_minutes": get_settings().commercial_revenue_escalation_cooldown_minutes,
        "max_retries": get_settings().commercial_revenue_escalation_max_retries,
        "totals": by_status,
        "failures": by_status.get("failed", 0),
        "retries": len([item for item in deliveries if item.retry_count > 0]),
        "suppressed": by_status.get("suppressed", 0),
        "deduplicated": by_status.get("deduplicated", 0),
        "delivery_types": by_delivery_type,
        "severity_routing": [
            {
                "policy": item.name,
                "severity_threshold": item.severity_threshold,
                "trigger_types": sanitize_alert_payload(item.trigger_types_json or []),
                "delivery_order": sanitize_alert_payload(item.escalation_order_json or item.allowed_delivery_types_json or []),
            }
            for item in policies
        ],
        "recent_deliveries": [
            {
                "id": str(item.id),
                "source_type": item.source_type,
                "source_id": item.source_id,
                "severity": item.severity,
                "delivery_type": item.delivery_type,
                "destination": item.destination,
                "status": item.status,
                "retry_count": item.retry_count,
                "response_code": item.response_code,
                "response_summary": item.response_summary,
                "created_at": item.created_at.isoformat(),
                "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
            }
            for item in deliveries[:20]
        ],
        "policies": [
            {
                "id": str(item.id),
                "name": item.name,
                "enabled": item.enabled,
                "severity_threshold": item.severity_threshold,
                "trigger_types_json": sanitize_alert_payload(item.trigger_types_json or []),
                "allowed_delivery_types_json": sanitize_alert_payload(item.allowed_delivery_types_json or []),
                "cooldown_minutes": item.cooldown_minutes,
                "max_retries": item.max_retries,
                "escalation_order_json": sanitize_alert_payload(item.escalation_order_json or []),
            }
            for item in policies
        ],
        "badges": [
            "DRY_RUN" if get_settings().commercial_revenue_escalations_mode == "dry_run" else None,
            "SENT" if by_status.get("sent") else None,
            "FAILED" if by_status.get("failed") else None,
            "SUPPRESSED" if by_status.get("suppressed") else None,
            "DEDUPED" if by_status.get("deduplicated") else None,
        ],
    }


async def _build_payload_for_retry(session: AsyncSession, delivery: CommercialRevenueAlertDelivery) -> dict[str, Any]:
    source_id = delivery.source_id
    source_type = delivery.source_type
    severity = delivery.severity
    summary = f"Revenue escalation retry for {source_type}:{source_id}"
    recommendation = "Retry the delivery and verify external notification channels."
    metadata: dict[str, Any] = {"retry": True}

    def _maybe_uuid(raw: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(raw)
        except (TypeError, ValueError):
            return None

    if source_type == "anomaly":
        anomaly_id = _maybe_uuid(source_id)
        anomaly = await session.get(CommercialFinancialAnomaly, anomaly_id) if anomaly_id else None
        if anomaly is not None:
            summary = anomaly.explanation or f"Critical anomaly {anomaly.anomaly_type}"
            recommendation = "Investigate anomaly root cause and verify cost/revenue integrity."
            metadata = sanitize_alert_payload(anomaly.metadata_json or {})
    elif source_type == "reconciliation":
        record_id = _maybe_uuid(source_id)
        record = await session.get(CommercialFinancialReconciliation, record_id) if record_id else None
        if record is not None:
            summary = record.notes or "Repeated reconciliation mismatches detected."
            recommendation = "Review mismatched ledger and chargeback records."
            metadata = sanitize_alert_payload(record.metadata_json or {})
    elif source_type == "dispute":
        dispute_id = _maybe_uuid(source_id)
        dispute = await session.get(CommercialBillingDispute, dispute_id) if dispute_id else None
        if dispute is not None:
            summary = dispute.disputed_reason
            recommendation = "Review dispute queue and customer impact."
    elif source_type == "policy_action":
        action_id = _maybe_uuid(source_id)
        action = await session.get(CommercialRevenueProtectionAction, action_id) if action_id else None
        if action is not None:
            summary = action.reason or f"Revenue protection action {action.action_type}"
            recommendation = "Inspect revenue protection state transitions."
            metadata = sanitize_alert_payload(action.after_state_json or {})

    return build_alert_payload(
        source_type=source_type,
        source_id=source_id,
        severity=severity,
        summary=summary,
        recommendation=recommendation,
        metadata=metadata,
        trigger_type=f"retry_{source_type}",
    )


async def retry_alert_delivery(session: AsyncSession, delivery_id: uuid.UUID) -> CommercialRevenueAlertDelivery:
    delivery = await session.get(CommercialRevenueAlertDelivery, delivery_id)
    if delivery is None:
        raise ValueError("delivery_not_found")
    max_retries = get_settings().commercial_revenue_escalation_max_retries
    if delivery.retry_count >= max_retries:
        raise ValueError("max_retries_exceeded")
    if delivery.last_retry_at is not None:
        backoff_seconds = apply_retry_backoff(delivery.retry_count)
        if utc_now() < delivery.last_retry_at + timedelta(seconds=backoff_seconds):
            raise ValueError("retry_backoff_active")

    payload = await _build_payload_for_retry(session, delivery)
    delivery.retry_count += 1
    delivery.last_retry_at = utc_now()
    try:
        if get_settings().commercial_revenue_escalations_mode == "dry_run":
            delivery.status = "dry_run"
            delivery.response_code = None
            delivery.response_summary = "retry_dry_run"
            delivery.delivered_at = utc_now()
        elif delivery.delivery_type == "webhook":
            result = await deliver_webhook(payload, max_retries=0)
            delivery.status = "sent"
            delivery.response_code = result.get("response_code")
            delivery.response_summary = _safe_string(result.get("response_summary") or result)
            delivery.delivered_at = utc_now()
        elif delivery.delivery_type == "slack":
            result = await deliver_slack(payload, max_retries=0)
            delivery.status = "sent"
            delivery.response_code = result.get("response_code")
            delivery.response_summary = _safe_string(result.get("response_summary") or result)
            delivery.delivered_at = utc_now()
        elif delivery.delivery_type == "pagerduty":
            result = await deliver_pagerduty(payload, dedupe_key=delivery.dedupe_key, max_retries=0)
            delivery.status = "sent"
            delivery.response_code = result.get("response_code")
            delivery.response_summary = _safe_string(result.get("response_summary") or result)
            delivery.delivered_at = utc_now()
        elif delivery.delivery_type == "email":
            result = await deliver_email(payload)
            delivery.status = "sent"
            delivery.response_code = result.get("response_code")
            delivery.response_summary = _safe_string(result.get("response_summary") or result)
            delivery.delivered_at = utc_now()
        else:
            raise ValueError("unsupported_delivery_type")
    except Exception as exc:
        delivery.status = "failed"
        delivery.response_summary = _safe_string(str(exc))
    await session.commit()
    await session.refresh(delivery)
    return delivery
