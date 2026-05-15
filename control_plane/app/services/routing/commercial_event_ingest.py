from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.models.commercial_routing_event_ingest import CommercialRoutingEventIngest
from app.schemas.routing import TaskType
from app.services.routing.commercial_report_export import REDACTION, SECRET_VALUE_PATTERNS, sanitize_report_payload

logger = logging.getLogger(__name__)


def _sanitize_text(value: str | None, *, limit: int = 500) -> str | None:
    if not value:
        return None
    sanitized = value
    for pattern in SECRET_VALUE_PATTERNS:
        sanitized = pattern.sub(REDACTION, sanitized)
    return sanitized[:limit]


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = payload or {}
    try:
        return sanitize_report_payload(raw)
    except HTTPException:
        sanitized: dict[str, Any] = {}
        for key, value in raw.items():
            lowered = str(key).lower()
            if any(part in lowered for part in {"api_key", "authorization", "secret", "token", "password", "prompt", "response"}):
                sanitized[str(key)] = REDACTION
            elif isinstance(value, str):
                sanitized[str(key)] = _sanitize_text(value, limit=2000)
            elif isinstance(value, dict):
                sanitized[str(key)] = _sanitize_payload(value)
            elif isinstance(value, list):
                sanitized[str(key)] = [
                    _sanitize_payload(item) if isinstance(item, dict) else (_sanitize_text(item, limit=2000) if isinstance(item, str) else item)
                    for item in value
                ]
            else:
                sanitized[str(key)] = value
        sanitized["sanitized_with_fallback"] = True
        return sanitized


def dedupe_event(
    correlation_id: str | None = None,
    request_id: str | None = None,
    event_id: str | None = None,
) -> str:
    parts = []
    if event_id:
        parts.append(f"event:{event_id}")
    if correlation_id:
        parts.append(f"corr:{correlation_id}")
    if request_id:
        parts.append(f"req:{request_id}")
    if parts:
        return "|".join(parts)
    return f"opaque:{uuid.uuid4()}"


async def mark_duplicate(
    db: AsyncSession,
    ingest: CommercialRoutingEventIngest,
    *,
    message: str | None = None,
) -> CommercialRoutingEventIngest:
    ingest.status = "duplicate"
    ingest.processed_at = utc_now()
    ingest.error_message = _sanitize_text(message or "duplicate routing event")
    await db.flush()
    return ingest


async def mark_failed(
    db: AsyncSession,
    ingest: CommercialRoutingEventIngest,
    *,
    message: str | None = None,
) -> CommercialRoutingEventIngest:
    ingest.status = "failed"
    ingest.processed_at = utc_now()
    ingest.error_message = _sanitize_text(message or "ingest processing failed")
    await db.flush()
    return ingest


async def ingest_routing_event(
    db: AsyncSession,
    payload: dict[str, Any],
    node_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    try:
        sanitized_payload = _sanitize_payload(payload)
        event_id = str(sanitized_payload.get("event_id") or sanitized_payload.get("commercial_routing_event_id") or "") or None
        correlation_id = sanitized_payload.get("correlation_id")
        request_id = sanitized_payload.get("request_id")
        dedupe_key = dedupe_event(correlation_id=correlation_id, request_id=request_id, event_id=event_id)

        status = "pending"
        if cfg.commercial_analytics_dedupe_enabled:
            existing = await db.execute(
                select(CommercialRoutingEventIngest).where(
                    CommercialRoutingEventIngest.dedupe_key == dedupe_key,
                    CommercialRoutingEventIngest.status.in_(["pending", "processed", "duplicate"]),
                )
            )
            if existing.scalars().first():
                status = "duplicate"

        ingest = CommercialRoutingEventIngest(
            event_id=event_id,
            correlation_id=correlation_id,
            request_id=request_id,
            node_id=node_id,
            status=status,
            dedupe_key=dedupe_key,
            processed_at=utc_now() if status == "duplicate" else None,
            error_message="duplicate routing event" if status == "duplicate" else None,
            payload_json=sanitized_payload,
        )
        db.add(ingest)
        await db.flush()
        return {
            "accepted": True,
            "id": str(ingest.id),
            "status": ingest.status,
            "dedupe_key": dedupe_key,
        }
    except Exception as exc:
        logger.warning("Commercial distributed ingest failed: %s", exc)
        return {
            "accepted": False,
            "status": "failed",
            "error": _sanitize_text(str(exc)),
        }


async def _find_existing_routing_event(
    db: AsyncSession,
    payload: dict[str, Any],
) -> CommercialRoutingEvent | None:
    event_uuid = payload.get("commercial_routing_event_id")
    if event_uuid:
        try:
            existing = await db.get(CommercialRoutingEvent, uuid.UUID(str(event_uuid)))
            if existing:
                return existing
        except (ValueError, TypeError):
            pass

    request_id = payload.get("request_id")
    correlation_id = payload.get("correlation_id")
    filters = []
    if request_id:
        filters.append(CommercialRoutingEvent.request_id == request_id)
    if correlation_id:
        filters.append(CommercialRoutingEvent.correlation_id == correlation_id)
    if not filters:
        return None
    result = await db.execute(select(CommercialRoutingEvent).where(or_(*filters)).order_by(CommercialRoutingEvent.created_at.desc()))
    return result.scalars().first()


def _task_type_from_payload(payload: dict[str, Any]) -> str | None:
    raw = payload.get("task_type")
    if raw is None:
        return None
    if isinstance(raw, TaskType):
        return raw.value
    return str(raw)


async def _create_routing_event_from_payload(
    db: AsyncSession,
    payload: dict[str, Any],
) -> CommercialRoutingEvent:
    client_id = payload.get("client_id")
    event = CommercialRoutingEvent(
        client_id=uuid.UUID(str(client_id)) if client_id else None,
        request_id=payload.get("request_id"),
        correlation_id=payload.get("correlation_id"),
        endpoint=payload.get("endpoint"),
        model_requested=payload.get("model_requested"),
        task_type=_task_type_from_payload(payload),
        policy=payload.get("policy"),
        selected_provider=payload.get("selected_provider"),
        selected_model=payload.get("selected_model"),
        selected_is_cloud=bool(payload.get("selected_is_cloud", False)),
        fallback_used=bool(payload.get("fallback_used", False)),
        blocked=bool(payload.get("blocked", False)),
        block_reason=payload.get("block_reason"),
        estimated_cost_brl=payload.get("estimated_cost_brl"),
        estimated_revenue_brl=payload.get("estimated_revenue_brl"),
        estimated_margin_brl=payload.get("estimated_margin_brl"),
        estimated_margin_percent=payload.get("estimated_margin_percent"),
        actual_cost_brl=payload.get("actual_cost_brl"),
        actual_revenue_brl=payload.get("actual_revenue_brl"),
        actual_margin_brl=payload.get("actual_margin_brl"),
        actual_margin_percent=payload.get("actual_margin_percent"),
        selected_score=payload.get("selected_score"),
        ranked_routes_json=payload.get("ranked_routes_json"),
        rejected_routes_json=payload.get("rejected_routes_json"),
        guardrail_decisions_json=payload.get("guardrail_decisions_json"),
        latency_ms=payload.get("latency_ms"),
        provider_latency_ms=payload.get("provider_latency_ms"),
        error_type=payload.get("error_type"),
        error_code=payload.get("error_code"),
        commercial_config_id=uuid.UUID(str(payload["commercial_config_id"])) if payload.get("commercial_config_id") else None,
        commercial_config_variant=payload.get("commercial_config_variant"),
    )
    db.add(event)
    await db.flush()
    return event


async def process_pending_events(
    db: AsyncSession,
    *,
    limit: int = 100,
    settings: Settings | None = None,
) -> dict[str, int]:
    cfg = settings or get_settings()
    result = await db.execute(
        select(CommercialRoutingEventIngest)
        .where(CommercialRoutingEventIngest.status == "pending")
        .order_by(CommercialRoutingEventIngest.received_at.asc())
        .limit(limit)
    )
    rows = result.scalars().all()
    summary = {"processed": 0, "duplicates": 0, "failed": 0}
    for ingest in rows:
        try:
            payload = ingest.payload_json or {}
            existing = await _find_existing_routing_event(db, payload)
            if existing is not None and payload.get("commercial_routing_event_id"):
                ingest.status = "processed"
                ingest.processed_at = utc_now()
                ingest.error_message = None
                await db.flush()
                summary["processed"] += 1
                continue
            if existing is not None and cfg.commercial_analytics_dedupe_enabled:
                await mark_duplicate(db, ingest, message="matching commercial routing event already exists")
                summary["duplicates"] += 1
                continue

            await _create_routing_event_from_payload(db, payload)
            ingest.status = "processed"
            ingest.processed_at = utc_now()
            ingest.error_message = None
            await db.flush()
            summary["processed"] += 1
        except Exception as exc:
            await mark_failed(db, ingest, message=str(exc))
            summary["failed"] += 1
    return summary
