from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from app.models.core.admin_action_log import AdminActionLog
from app.schemas.routing import TaskType
from app.services.routing.commercial_event_ingest import ingest_routing_event
from app.services.routing.commercial_node_heartbeat import resolve_node_identity
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def record_routing_event(
    db: AsyncSession,
    client_id: uuid.UUID | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    endpoint: str | None = None,
    model_requested: str | None = None,
    task_type: TaskType | None = None,
    policy: str | None = None,
    selected_provider: str | None = None,
    selected_model: str | None = None,
    selected_is_cloud: bool = False,
    fallback_used: bool = False,
    blocked: bool = False,
    block_reason: str | None = None,
    estimated_cost_brl: float | None = None,
    estimated_revenue_brl: float | None = None,
    estimated_margin_brl: float | None = None,
    estimated_margin_percent: float | None = None,
    selected_score: float | None = None,
    ranked_routes: list[Any] | None = None,
    rejected_routes: list[Any] | None = None,
    guardrail_decisions: list[Any] | None = None,
    commercial_config_id: uuid.UUID | None = None,
    commercial_config_variant: str | None = None,
    qos_tier: str | None = None,
    sla_pass: bool | None = None,
    degradation_applied: str | None = None,
    qos_priority: int | None = None,
) -> uuid.UUID | None:
    """
    Records a commercial routing event in the database.
    Best-effort: does not raise exceptions to avoid breaking the main flow.
    """
    try:
        # Sanitization: never save prompts, responses, or secrets
        sanitized_ranked = _sanitize_routes(ranked_routes)
        sanitized_rejected = _sanitize_routes(rejected_routes)
        sanitized_guardrails = _sanitize_guardrails(guardrail_decisions)

        event = CommercialRoutingEvent(
            client_id=client_id,
            request_id=request_id,
            correlation_id=correlation_id,
            endpoint=endpoint,
            model_requested=model_requested,
            task_type=task_type.value if task_type else None,
            policy=policy,
            selected_provider=selected_provider,
            selected_model=selected_model,
            selected_is_cloud=selected_is_cloud,
            fallback_used=fallback_used,
            blocked=blocked,
            block_reason=block_reason,
            estimated_cost_brl=estimated_cost_brl,
            estimated_revenue_brl=estimated_revenue_brl,
            estimated_margin_brl=estimated_margin_brl,
            estimated_margin_percent=estimated_margin_percent,
            selected_score=selected_score,
            ranked_routes_json={"routes": sanitized_ranked} if sanitized_ranked else None,
            rejected_routes_json={"routes": sanitized_rejected} if sanitized_rejected else None,
            guardrail_decisions_json={"decisions": sanitized_guardrails}
            if sanitized_guardrails
            else None,
            commercial_config_id=commercial_config_id,
            commercial_config_variant=commercial_config_variant,
            qos_tier=qos_tier,
            sla_pass=sla_pass,
            degradation_applied=degradation_applied,
            qos_priority=qos_priority,
        )
        db.add(event)
        await (
            db.flush()
        )  # Flush to get the ID but don't commit yet (depends on the caller's transaction)
        settings = get_settings()
        if settings.commercial_distributed_analytics_enabled:
            identity = resolve_node_identity(settings)
            await ingest_routing_event(
                db,
                {
                    "commercial_routing_event_id": str(event.id),
                    "client_id": str(client_id) if client_id else None,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "endpoint": endpoint,
                    "model_requested": model_requested,
                    "task_type": task_type.value if task_type else None,
                    "policy": policy,
                    "selected_provider": selected_provider,
                    "selected_model": selected_model,
                    "selected_is_cloud": selected_is_cloud,
                    "fallback_used": fallback_used,
                    "blocked": blocked,
                    "block_reason": block_reason,
                    "estimated_cost_brl": estimated_cost_brl,
                    "estimated_revenue_brl": estimated_revenue_brl,
                    "estimated_margin_brl": estimated_margin_brl,
                    "estimated_margin_percent": estimated_margin_percent,
                    "selected_score": selected_score,
                    "ranked_routes_json": {"routes": sanitized_ranked}
                    if sanitized_ranked
                    else None,
                    "rejected_routes_json": {"routes": sanitized_rejected}
                    if sanitized_rejected
                    else None,
                    "guardrail_decisions_json": {"decisions": sanitized_guardrails}
                    if sanitized_guardrails
                    else None,
                    "commercial_config_id": str(commercial_config_id)
                    if commercial_config_id
                    else None,
                    "commercial_config_variant": commercial_config_variant,
                },
                identity["node_id"],
                settings=settings,
            )
        return event.id
    except Exception as e:
        logger.error(f"Failed to record commercial routing event: {e}", exc_info=True)
        return None


async def update_actual_financials(
    db: AsyncSession,
    request_id: str | None = None,
    correlation_id: str | None = None,
    actual_cost_brl: float = 0.0,
    actual_revenue_brl: float = 0.0,
    latency_ms: int | None = None,
    provider_latency_ms: int | None = None,
    error_type: str | None = None,
    error_code: str | None = None,
) -> bool:
    """
    Updates a routing event with actual financial and performance data.
    """
    try:
        stmt = select(CommercialRoutingEvent)
        if request_id:
            stmt = stmt.where(CommercialRoutingEvent.request_id == request_id)
        elif correlation_id:
            stmt = stmt.where(CommercialRoutingEvent.correlation_id == correlation_id)
        else:
            return False

        result = await db.execute(stmt)
        # Get the most recent one if multiple matches (though correlation_id should be unique-ish)
        event = result.scalars().first()

        if not event:
            return False

        event.actual_cost_brl = actual_cost_brl
        event.actual_revenue_brl = actual_revenue_brl
        event.actual_margin_brl = actual_revenue_brl - actual_cost_brl
        if actual_revenue_brl > 0:
            event.actual_margin_percent = (event.actual_margin_brl / actual_revenue_brl) * 100
        else:
            event.actual_margin_percent = -100.0 if actual_cost_brl > 0 else 0.0

        if latency_ms is not None:
            event.latency_ms = latency_ms
        if provider_latency_ms is not None:
            event.provider_latency_ms = provider_latency_ms
        if error_type:
            event.error_type = error_type
        if error_code:
            event.error_code = error_code

        await db.flush()
        return True
    except Exception as e:
        logger.error(
            f"Failed to update actual financials for routing event {request_id}: {e}", exc_info=True
        )
        return False


async def summarize_today(db: AsyncSession) -> dict[str, Any]:
    """
    Returns a summary of today's commercial routing events.
    """
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())

    # Base filters
    filters = [CommercialRoutingEvent.created_at >= start_of_day]

    # Total counts
    stmt_counts = select(
        func.count(CommercialRoutingEvent.id).label("total"),
        func.count(CommercialRoutingEvent.id)
        .filter(CommercialRoutingEvent.fallback_used == True)
        .label("fallbacks"),
        func.count(CommercialRoutingEvent.id)
        .filter(CommercialRoutingEvent.blocked == True)
        .label("blocks"),
    ).where(*filters)

    res_counts = await db.execute(stmt_counts)
    counts = res_counts.one()

    # Financials
    stmt_fin = select(
        func.sum(CommercialRoutingEvent.estimated_revenue_brl).label("est_rev"),
        func.sum(CommercialRoutingEvent.estimated_cost_brl).label("est_cost"),
        func.sum(CommercialRoutingEvent.actual_revenue_brl).label("act_rev"),
        func.sum(CommercialRoutingEvent.actual_cost_brl).label("act_cost"),
    ).where(*filters)

    res_fin = await db.execute(stmt_fin)
    fin = res_fin.one()

    est_rev = float(fin.est_rev or 0)
    est_cost = float(fin.est_cost or 0)
    act_rev = float(fin.act_rev or 0)
    act_cost = float(fin.act_cost or 0)

    est_margin = est_rev - est_cost
    act_margin = act_rev - act_cost

    est_err_pct = 0.0
    if act_rev > 0:
        est_err_pct = abs((est_rev - act_rev) / act_rev) * 100

    # Selected by provider
    stmt_prov = (
        select(CommercialRoutingEvent.selected_provider, func.count(CommercialRoutingEvent.id))
        .where(*filters)
        .group_by(CommercialRoutingEvent.selected_provider)
    )

    res_prov = await db.execute(stmt_prov)
    providers = {row[0]: row[1] for row in res_prov.all() if row[0]}

    return {
        "events_today": counts.total,
        "selected_by_provider": providers,
        "fallback_count_today": counts.fallbacks,
        "blocked_count_today": counts.blocks,
        "estimated_revenue_today_brl": round(est_rev, 4),
        "estimated_cost_today_brl": round(est_cost, 4),
        "estimated_margin_today_brl": round(est_margin, 4),
        "actual_revenue_today_brl": round(act_rev, 4),
        "actual_cost_today_brl": round(act_cost, 4),
        "actual_margin_today_brl": round(act_margin, 4),
        "estimation_error_percent": round(est_err_pct, 2),
    }


async def list_recent_events(
    db: AsyncSession,
    limit: int = 50,
    client_id: uuid.UUID | None = None,
    provider: str | None = None,
    blocked: bool | None = None,
    fallback_used: bool | None = None,
) -> list[CommercialRoutingEvent]:
    stmt = select(CommercialRoutingEvent).order_by(CommercialRoutingEvent.created_at.desc())

    filters = []
    if client_id:
        filters.append(CommercialRoutingEvent.client_id == client_id)
    if provider:
        filters.append(CommercialRoutingEvent.selected_provider == provider)
    if blocked is not None:
        filters.append(CommercialRoutingEvent.blocked == blocked)
    if fallback_used is not None:
        filters.append(CommercialRoutingEvent.fallback_used == fallback_used)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _sanitize_routes(routes: list[Any] | None) -> list[dict[str, Any]] | None:
    if not routes:
        return None

    sanitized = []
    for r in routes:
        # Convert to dict if it's a Pydantic model or similar
        item = r.dict() if hasattr(r, "dict") else (r if isinstance(r, dict) else vars(r))

        # Explicitly keep only safe fields
        safe_item = {
            "provider": item.get("provider"),
            "model": item.get("model"),
            "score": item.get("score"),
            "estimated_cost_brl": item.get("estimated_cost_brl"),
            "estimated_revenue_brl": item.get("estimated_revenue_brl"),
            "estimated_margin_percent": item.get("estimated_margin_percent"),
            "rejection_reasons": item.get("rejection_reasons") or item.get("rejection_reason"),
            "is_cloud": item.get("is_cloud"),
        }
        sanitized.append(safe_item)
    return sanitized


def _sanitize_guardrails(decisions: list[Any] | None) -> list[dict[str, Any]] | None:
    if not decisions:
        return None
    sanitized = []
    for d in decisions:
        item = d if isinstance(d, dict) else vars(d)
        safe_item = {
            "guardrail": item.get("guardrail") or item.get("name"),
            "passed": item.get("passed"),
            "action": item.get("action"),
            "reason": item.get("reason"),
        }
        sanitized.append(safe_item)
    return sanitized


async def audit_log(
    db: AsyncSession,
    event_type: str,
    client_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Logs an administrative or system action.
    """
    try:
        log = AdminActionLog(
            action=event_type,
            admin_role="admin",
            target_user_id=client_id,
            payload_json=details or {},
            status="success",
        )
        db.add(log)
        await db.flush()
    except Exception as e:
        logger.error(f"Failed to log audit event {event_type}: {e}", exc_info=True)
