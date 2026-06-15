from __future__ import annotations

import logging
from collections import Counter, deque
from datetime import UTC, datetime
from datetime import time as dt_time
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.models.billing.request_financial import RequestFinancial
from app.models.core.client import Client
from app.services.billing.pricing_engine import calculate_customer_price, estimate_provider_cost
from app.services.billing.revenue_protection import get_active_revenue_protection_constraints
from app.services.provider_classification import (
    classify_provider,
    is_cloud_provider,
    is_local_provider,
    normalize_provider_name,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
WARNING_LIMIT_RATIO = 0.8
_RUNTIME_EVENTS: deque[dict[str, Any]] = deque(maxlen=5000)


def _today_start_utc(now_utc: datetime | None = None) -> datetime:
    current = now_utc or datetime.now(UTC)
    return datetime.combine(current.date(), dt_time.min, tzinfo=UTC)


def _margin_percent(profit_brl: float, revenue_brl: float) -> float:
    if revenue_brl <= 0:
        return 0.0
    return (profit_brl / revenue_brl) * 100.0


def _warning_limit(limit_brl: float) -> float | None:
    if limit_brl <= 0:
        return None
    return limit_brl * WARNING_LIMIT_RATIO


def _build_mode(settings) -> str:
    block_mode = getattr(settings, "negative_margin_block_mode", "report_only")
    if not settings.commercial_guardrails_enabled or block_mode == "disabled":
        return "disabled"
    if block_mode == "report_only":
        return "report_only"
    return "enforce_cloud_only"


def _append_unique(target: list[str], message: str) -> None:
    if message not in target:
        target.append(message)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _sanitize_reason_code(value: str) -> str:
    return value.replace(" ", "_").replace("-", "_")[:64]


def clear_commercial_guardrail_runtime_events() -> None:
    _RUNTIME_EVENTS.clear()


def record_commercial_guardrail_event(
    *,
    event_type: str,
    provider: str | None,
    client_id: str | None,
    reason_code: str,
    enforcement_mode: str,
    fallback_used: bool,
    fallback_provider: str | None = None,
) -> None:
    event = {
        "timestamp": _now_utc().isoformat(),
        "event_type": event_type,
        "provider": provider,
        "client_id": client_id,
        "reason_code": _sanitize_reason_code(reason_code),
        "enforcement_mode": enforcement_mode,
        "fallback_used": fallback_used,
        "fallback_provider": fallback_provider,
    }
    _RUNTIME_EVENTS.append(event)
    logger.info(
        event_type,
        extra={
            "extra_data": {
                "provider": provider,
                "client_id": client_id,
                "reason_code": event["reason_code"],
                "enforcement_mode": enforcement_mode,
                "fallback_used": fallback_used,
                "fallback_provider": fallback_provider,
            }
        },
    )


def _local_routes_available(routes: list[Any]) -> bool:
    return any(
        is_local_provider(getattr(getattr(route, "inference_backend", None), "provider", None))
        for route in routes
    )


def get_commercial_guardrails_runtime_status() -> dict[str, Any]:
    settings = get_settings()
    mode = _build_mode(settings)
    today_prefix = _now_utc().date().isoformat()
    todays_events = [
        event
        for event in _RUNTIME_EVENTS
        if str(event.get("timestamp", "")).startswith(today_prefix)
    ]

    blocked = [
        event for event in todays_events if event["event_type"] == "commercial_guardrail_blocked"
    ]
    fallbacks = [
        event for event in todays_events if event["event_type"] == "commercial_guardrail_fallback"
    ]
    report_only = [
        event
        for event in todays_events
        if event["event_type"] == "commercial_guardrail_triggered"
        and event["enforcement_mode"] == "report_only"
    ]

    fallback_counter = Counter(
        event.get("fallback_provider") for event in fallbacks if event.get("fallback_provider")
    )
    providers_blocked = sorted(
        {event.get("provider") for event in blocked if event.get("provider")}
    )
    clients_affected = sorted(
        {event.get("client_id") for event in todays_events if event.get("client_id")}
    )

    return {
        "enforcement_mode": mode,
        "cloud_kill_switch": bool(getattr(settings, "global_cloud_kill_switch", False)),
        "local_fallback_enabled": True,
        "blocked_cloud_requests_today": len(blocked),
        "successful_local_fallbacks_today": len(fallbacks),
        "report_only_events_today": len(report_only),
        "providers_blocked": providers_blocked,
        "clients_affected": clients_affected,
        "top_fallback_providers": [
            {"provider": provider, "count": count}
            for provider, count in fallback_counter.most_common(5)
        ],
    }


def build_openai_guardrail_error_payload() -> dict[str, Any]:
    return {
        "error": {
            "message": "Cloud provider temporarily unavailable due to operational guardrails.",
            "type": "commercial_guardrail_block",
            "code": "cloud_provider_blocked",
        }
    }


def _estimated_financials_for_provider(
    *,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    plan_code: str | None,
) -> dict[str, float]:
    provider_cost = estimate_provider_cost(provider, prompt_tokens, completion_tokens).cost_brl
    customer_price = calculate_customer_price(plan_code, prompt_tokens, completion_tokens).price_brl
    return {
        "estimated_cost_brl": float(provider_cost),
        "estimated_revenue_brl": float(customer_price),
    }


async def build_runtime_enforcement_context(
    session: AsyncSession,
    *,
    client_id: str,
    plan_code: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    now_utc = _now_utc()
    today_start = _today_start_utc(now_utc)
    try:
        client_identifier: str | UUID = UUID(client_id)
    except ValueError:
        client_identifier = client_id

    stmt_global = select(
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("provider_cost"),
    ).where(RequestFinancial.created_at >= today_start)
    row_global = (await session.execute(stmt_global)).first()

    stmt_provider = (
        select(
            RequestFinancial.provider,
            func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("provider_cost"),
        )
        .where(RequestFinancial.created_at >= today_start)
        .group_by(RequestFinancial.provider)
    )
    provider_rows = (await session.execute(stmt_provider)).all()

    stmt_client = select(
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("provider_cost"),
        func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("revenue"),
        func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
    ).where(
        RequestFinancial.created_at >= today_start,
        RequestFinancial.client_id == client_identifier,
    )
    row_client = (await session.execute(stmt_client)).first()

    return {
        "generated_at_utc": now_utc.isoformat(),
        "enforcement_mode": _build_mode(settings),
        "cloud_kill_switch": bool(getattr(settings, "global_cloud_kill_switch", False)),
        "client_id": client_id,
        "plan_code": plan_code,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "global_provider_cost_today_brl": float(row_global.provider_cost or 0.0),
        "provider_costs_today_brl": {
            row.provider or "unknown": float(row.provider_cost or 0.0) for row in provider_rows
        },
        "client_cost_today_brl": float(row_client.provider_cost or 0.0),
        "client_revenue_today_brl": float(row_client.revenue or 0.0),
        "client_margin_today_brl": float(row_client.profit or 0.0),
        "max_global_provider_cost_per_day_brl": float(
            settings.max_global_provider_cost_per_day_brl
        ),
        "max_provider_cost_per_day_brl": float(settings.max_provider_cost_per_day_brl),
        "max_client_provider_cost_per_day_brl": float(
            settings.max_client_provider_cost_per_day_brl
        ),
        "margin_warning_percent": float(settings.margin_warning_percent),
        "estimated_by_provider": {},
        "report_only_candidates": [],
        "blocked_candidates": [],
        "would_block": [],
        "guardrail_fallback_active": False,
        "blocked_without_fallback": False,
        "local_fallback_enabled": True,
        "revenue_protection_constraints": get_active_revenue_protection_constraints(
            client_id=client_id
        ),
    }


def evaluate_provider_candidate_against_guardrails(
    context: dict[str, Any] | None,
    provider: str,
) -> dict[str, Any]:
    provider_name = normalize_provider_name(provider or "unknown")
    if not context or not is_cloud_provider(provider_name):
        return {
            "blocked": False,
            "reasons": [],
            "estimated_cost_brl": 0.0,
            "estimated_revenue_brl": 0.0,
        }

    estimates = context.setdefault("estimated_by_provider", {})
    if provider_name not in estimates:
        estimates[provider_name] = _estimated_financials_for_provider(
            provider=provider_name,
            prompt_tokens=int(context.get("prompt_tokens", 0)),
            completion_tokens=int(context.get("completion_tokens", 0)),
            plan_code=context.get("plan_code"),
        )
    estimated = estimates[provider_name]

    reasons: list[str] = []
    projected_global_cost = float(context.get("global_provider_cost_today_brl", 0.0)) + float(
        estimated["estimated_cost_brl"]
    )
    projected_provider_cost = float(
        context.get("provider_costs_today_brl", {}).get(provider_name, 0.0)
    ) + float(estimated["estimated_cost_brl"])
    projected_client_cost = float(context.get("client_cost_today_brl", 0.0)) + float(
        estimated["estimated_cost_brl"]
    )
    projected_client_revenue = float(context.get("client_revenue_today_brl", 0.0)) + float(
        estimated["estimated_revenue_brl"]
    )
    projected_client_margin = float(context.get("client_margin_today_brl", 0.0)) + (
        float(estimated["estimated_revenue_brl"]) - float(estimated["estimated_cost_brl"])
    )
    projected_margin_percent = _margin_percent(projected_client_margin, projected_client_revenue)

    if context.get("cloud_kill_switch"):
        reasons.append("global_cloud_kill_switch")
    if float(
        context.get("max_global_provider_cost_per_day_brl", 0.0)
    ) > 0 and projected_global_cost >= float(context["max_global_provider_cost_per_day_brl"]):
        reasons.append("global_daily_cost_limit_exceeded")
    if float(
        context.get("max_provider_cost_per_day_brl", 0.0)
    ) > 0 and projected_provider_cost >= float(context["max_provider_cost_per_day_brl"]):
        reasons.append("provider_daily_cost_limit_exceeded")
    if float(
        context.get("max_client_provider_cost_per_day_brl", 0.0)
    ) > 0 and projected_client_cost >= float(context["max_client_provider_cost_per_day_brl"]):
        reasons.append("client_daily_cost_limit_exceeded")
    if projected_client_margin < 0:
        reasons.append("negative_margin")
    elif projected_margin_percent < float(context.get("margin_warning_percent", 0.0)):
        reasons.append("margin_below_threshold")

    return {
        "blocked": any(
            reason
            in {
                "global_cloud_kill_switch",
                "global_daily_cost_limit_exceeded",
                "provider_daily_cost_limit_exceeded",
                "client_daily_cost_limit_exceeded",
                "negative_margin",
            }
            for reason in reasons
        ),
        "reasons": reasons,
        "estimated_cost_brl": float(estimated["estimated_cost_brl"]),
        "estimated_revenue_brl": float(estimated["estimated_revenue_brl"]),
        "projected_client_margin_brl": projected_client_margin,
        "projected_client_margin_percent": projected_margin_percent,
    }


def filter_routes_by_commercial_guardrails(
    routes: list[Any], context: dict[str, Any] | None
) -> list[Any]:
    if not context:
        return routes
    mode = context.get("enforcement_mode", "disabled")
    if mode == "disabled":
        context["local_routes_available"] = _local_routes_available(routes)
        context["cloud_routes_available_after_filter"] = any(
            is_cloud_provider(getattr(getattr(route, "inference_backend", None), "provider", None))
            for route in routes
        )
        return routes

    filtered: list[Any] = []
    report_only_candidates: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []

    for route in routes:
        backend = getattr(route, "inference_backend", None)
        provider = getattr(backend, "provider", None)
        if not is_cloud_provider(provider):
            filtered.append(route)
            continue

        evaluation = evaluate_provider_candidate_against_guardrails(context, provider)
        if not evaluation["blocked"]:
            filtered.append(route)
            continue

        candidate = {
            "provider": provider,
            "reasons": list(evaluation["reasons"]),
            "estimated_cost_brl": round(float(evaluation["estimated_cost_brl"]), 4),
            "estimated_revenue_brl": round(float(evaluation["estimated_revenue_brl"]), 4),
        }
        if mode == "report_only":
            report_only_candidates.append(candidate)
            filtered.append(route)
        elif mode == "enforce_cloud_only":
            blocked_candidates.append(candidate)
        else:
            filtered.append(route)

    context["report_only_candidates"] = report_only_candidates
    context["blocked_candidates"] = blocked_candidates
    context["blocked_cloud_providers"] = [item["provider"] for item in blocked_candidates]
    context["local_routes_available"] = _local_routes_available(
        filtered
    ) or _local_routes_available(routes)
    context["cloud_routes_available_after_filter"] = any(
        is_cloud_provider(getattr(getattr(route, "inference_backend", None), "provider", None))
        for route in filtered
    )
    context["would_block"] = [
        {
            "type": "provider_daily_cost",
            "provider": item["provider"],
            "action": "would_block_cloud_provider",
            "reasons": item["reasons"],
        }
        for item in blocked_candidates
    ]
    context["guardrail_fallback_active"] = bool(
        blocked_candidates and context["local_routes_available"]
    )
    context["blocked_without_fallback"] = bool(blocked_candidates and not filtered)
    return filtered


def record_report_only_events(context: dict[str, Any] | None) -> None:
    if not context or context.get("enforcement_mode") != "report_only":
        return
    client_id = str(context.get("client_id") or "")
    for item in context.get("report_only_candidates") or []:
        reasons = item.get("reasons") or ["report_only"]
        record_commercial_guardrail_event(
            event_type="commercial_guardrail_triggered",
            provider=item.get("provider"),
            client_id=client_id or None,
            reason_code=str(reasons[0]),
            enforcement_mode="report_only",
            fallback_used=False,
        )


def record_enforcement_outcome(
    context: dict[str, Any] | None,
    *,
    selected_provider: str | None = None,
    blocked_without_fallback: bool = False,
) -> None:
    if not context:
        return
    mode = context.get("enforcement_mode", "disabled")
    if mode == "disabled":
        return

    client_id = str(context.get("client_id") or "") or None
    selected_provider_name = normalize_provider_name(selected_provider)

    if blocked_without_fallback or context.get("blocked_without_fallback"):
        for item in context.get("blocked_candidates") or []:
            reasons = item.get("reasons") or ["blocked"]
            record_commercial_guardrail_event(
                event_type="commercial_guardrail_blocked",
                provider=item.get("provider"),
                client_id=client_id,
                reason_code=str(reasons[0]),
                enforcement_mode=mode,
                fallback_used=False,
            )
        return

    if (
        mode == "enforce_cloud_only"
        and context.get("guardrail_fallback_active")
        and is_local_provider(selected_provider_name)
    ):
        for item in context.get("blocked_candidates") or []:
            reasons = item.get("reasons") or ["fallback"]
            record_commercial_guardrail_event(
                event_type="commercial_guardrail_fallback",
                provider=item.get("provider"),
                client_id=client_id,
                reason_code=str(reasons[0]),
                enforcement_mode=mode,
                fallback_used=True,
                fallback_provider=selected_provider_name or None,
            )


async def build_commercial_guardrails_overview(session: AsyncSession) -> dict[str, Any]:
    settings = get_settings()
    now_utc = datetime.now(UTC)
    today_start = _today_start_utc(now_utc)
    mode = _build_mode(settings)

    global_limit = float(settings.max_global_provider_cost_per_day_brl)
    provider_limit = float(settings.max_provider_cost_per_day_brl)
    client_limit = float(settings.max_client_provider_cost_per_day_brl)
    margin_warning_percent = float(settings.margin_warning_percent)

    warnings: list[str] = []
    recommendations: list[str] = []
    would_block: list[dict[str, Any]] = []
    providers_over_warning_threshold: list[str] = []
    providers_over_block_threshold: list[str] = []
    clients_over_warning_threshold: list[str] = []
    clients_over_block_threshold: list[str] = []
    clients_with_negative_margin: list[str] = []

    stmt_global = select(
        func.count(RequestFinancial.id).label("requests"),
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("provider_cost"),
        func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("revenue"),
        func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
    ).where(RequestFinancial.created_at >= today_start)
    row_global = (await session.execute(stmt_global)).first()

    global_request_count_today = int(row_global.requests or 0)
    global_provider_cost_today_brl = float(row_global.provider_cost or 0.0)
    global_revenue_today_brl = float(row_global.revenue or 0.0)
    global_margin_today_brl = float(row_global.profit or 0.0)
    global_margin_percent_today = _margin_percent(global_margin_today_brl, global_revenue_today_brl)

    stmt_provider = (
        select(
            RequestFinancial.provider,
            func.count(RequestFinancial.id).label("requests"),
            func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost"),
            func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("revenue"),
            func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
        )
        .where(RequestFinancial.created_at >= today_start)
        .group_by(RequestFinancial.provider)
    )
    provider_rows = (await session.execute(stmt_provider)).all()

    providers: list[dict[str, Any]] = []
    global_cloud_provider_cost_today_brl = 0.0
    provider_warning_limit = _warning_limit(provider_limit)
    global_warning_limit = _warning_limit(global_limit)

    for row in provider_rows:
        provider = row.provider or "unknown"
        requests = int(row.requests or 0)
        cost_brl = float(row.cost or 0.0)
        revenue_brl = float(row.revenue or 0.0)
        margin_brl = float(row.profit or 0.0)
        margin_percent = _margin_percent(margin_brl, revenue_brl)
        provider_is_cloud = classify_provider(provider) == "cloud"
        if provider_is_cloud:
            global_cloud_provider_cost_today_brl += cost_brl

        over_warning = bool(
            provider_warning_limit is not None and cost_brl >= provider_warning_limit
        )
        over_block = bool(provider_limit > 0 and cost_brl >= provider_limit)
        status = "ok"
        if over_block:
            status = "would_block"
        elif over_warning:
            status = "warning"

        if over_warning:
            providers_over_warning_threshold.append(provider)
            _append_unique(warnings, f"Provider '{provider}' acima do threshold de alerta diário.")
            _append_unique(
                recommendations, f"Revisar pricing e roteamento do provider '{provider}'."
            )
        if over_block:
            providers_over_block_threshold.append(provider)
            would_block.append(
                {
                    "type": "provider_daily_cost",
                    "provider": provider,
                    "current_cost_brl": round(cost_brl, 2),
                    "limit_brl": round(provider_limit, 2),
                    "action": "would_block_cloud_provider"
                    if provider_is_cloud
                    else "would_block_provider",
                }
            )

        providers.append(
            {
                "provider": provider,
                "provider_cost_today_brl": round(cost_brl, 2),
                "provider_request_count_today": requests,
                "provider_revenue_today_brl": round(revenue_brl, 2),
                "provider_margin_today_brl": round(margin_brl, 2),
                "provider_margin_percent_today": round(margin_percent, 2),
                "warning_limit_brl": round(provider_warning_limit, 2)
                if provider_warning_limit is not None
                else None,
                "block_limit_brl": round(provider_limit, 2) if provider_limit > 0 else None,
                "is_cloud_provider": provider_is_cloud,
                "over_warning_threshold": over_warning,
                "over_block_threshold": over_block,
                "status": status,
            }
        )

    if global_warning_limit is not None and global_provider_cost_today_brl >= global_warning_limit:
        _append_unique(warnings, "Custo global diário de providers acima do threshold de alerta.")
        _append_unique(
            recommendations, "Reduzir fallback cloud e revisar tenants com maior consumo."
        )
    if global_limit > 0 and global_provider_cost_today_brl >= global_limit:
        would_block.append(
            {
                "type": "global_provider_daily_cost",
                "provider": "all",
                "current_cost_brl": round(global_provider_cost_today_brl, 2),
                "limit_brl": round(global_limit, 2),
                "action": "would_block_all_cloud_providers",
            }
        )

    stmt_client = (
        select(
            RequestFinancial.client_id,
            Client.name,
            func.count(RequestFinancial.id).label("requests"),
            func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost"),
            func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("revenue"),
            func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
        )
        .outerjoin(Client, Client.id == RequestFinancial.client_id)
        .where(RequestFinancial.created_at >= today_start)
        .group_by(RequestFinancial.client_id, Client.name)
    )
    client_rows = (await session.execute(stmt_client)).all()

    clients: list[dict[str, Any]] = []
    client_warning_limit = _warning_limit(client_limit)
    for row in client_rows:
        client_id = str(row.client_id)
        client_name = row.name or "unknown"
        requests = int(row.requests or 0)
        cost_brl = float(row.cost or 0.0)
        revenue_brl = float(row.revenue or 0.0)
        margin_brl = float(row.profit or 0.0)
        margin_percent = _margin_percent(margin_brl, revenue_brl)
        over_warning = bool(client_warning_limit is not None and cost_brl >= client_warning_limit)
        over_block = bool(client_limit > 0 and cost_brl >= client_limit)
        margin_warning = margin_percent < margin_warning_percent
        negative_margin = margin_brl < 0

        status = "ok"
        if over_block or negative_margin:
            status = "would_block"
        elif over_warning or margin_warning:
            status = "warning"

        if negative_margin:
            clients_with_negative_margin.append(client_id)
            _append_unique(warnings, f"Cliente '{client_name}' opera com margem negativa hoje.")
            _append_unique(
                recommendations, f"Revisar preço, cache e fallback do cliente '{client_name}'."
            )
            would_block.append(
                {
                    "type": "negative_margin",
                    "client_id": client_id,
                    "client_name": client_name,
                    "current_margin_brl": round(margin_brl, 2),
                    "margin_percent": round(margin_percent, 2),
                    "action": "would_block_negative_margin_client",
                }
            )
        elif margin_warning:
            _append_unique(warnings, f"Cliente '{client_name}' abaixo do threshold de margem.")

        if over_warning:
            clients_over_warning_threshold.append(client_id)
            _append_unique(warnings, f"Cliente '{client_name}' acima do threshold de custo diário.")
        if over_block:
            clients_over_block_threshold.append(client_id)
            would_block.append(
                {
                    "type": "client_daily_cost",
                    "client_id": client_id,
                    "client_name": client_name,
                    "current_cost_brl": round(cost_brl, 2),
                    "limit_brl": round(client_limit, 2),
                    "action": "would_block_client_cloud_usage",
                }
            )

        clients.append(
            {
                "client_id": client_id,
                "client_name": client_name,
                "client_request_count_today": requests,
                "client_cost_today_brl": round(cost_brl, 2),
                "client_revenue_today_brl": round(revenue_brl, 2),
                "client_margin_today_brl": round(margin_brl, 2),
                "client_margin_percent_today": round(margin_percent, 2),
                "warning_limit_brl": round(client_warning_limit, 2)
                if client_warning_limit is not None
                else None,
                "block_limit_brl": round(client_limit, 2) if client_limit > 0 else None,
                "margin_warning_threshold_percent": round(margin_warning_percent, 2),
                "is_negative_margin": negative_margin,
                "over_warning_threshold": over_warning,
                "over_block_threshold": over_block,
                "is_below_margin_warning": margin_warning,
                "status": status,
            }
        )

    if not settings.cloud_providers_enabled:
        _append_unique(
            recommendations,
            "Cloud permanece desabilitada por padrão; usar guardrails como readiness operacional.",
        )
    if getattr(settings, "global_cloud_kill_switch", False):
        _append_unique(warnings, "GLOBAL_CLOUD_KILL_SWITCH ativo: providers cloud indisponíveis.")
        _append_unique(
            recommendations,
            "Desativar o kill switch apenas quando houver janela operacional segura.",
        )
        would_block.append(
            {
                "type": "global_cloud_kill_switch",
                "provider": "all",
                "current_cost_brl": round(global_cloud_provider_cost_today_brl, 2),
                "limit_brl": None,
                "action": "would_block_all_cloud_providers",
            }
        )
    if mode == "disabled":
        _append_unique(
            recommendations,
            "Habilitar COMMERCIAL_GUARDRAILS_ENABLED=true apenas para observabilidade admin-only.",
        )
    elif mode == "report_only":
        _append_unique(
            recommendations,
            "Acompanhar o relatório por alguns dias antes de ativar enforce_cloud_only.",
        )
    else:
        _append_unique(
            recommendations,
            "Enforcement ativo apenas para cloud; revisar fallback local-first e kill switch antes de ampliar rollout.",
        )

    providers.sort(key=lambda item: item["provider_cost_today_brl"], reverse=True)
    clients.sort(key=lambda item: item["client_cost_today_brl"], reverse=True)

    return {
        "generated_at_utc": now_utc.isoformat(),
        "mode": mode,
        "global_limits": {
            "commercial_guardrails_enabled": settings.commercial_guardrails_enabled,
            "max_global_provider_cost_per_day_brl": round(global_limit, 2),
            "max_provider_cost_per_day_brl": round(provider_limit, 2),
            "max_client_provider_cost_per_day_brl": round(client_limit, 2),
            "margin_warning_percent": round(margin_warning_percent, 2),
            "negative_margin_block_mode": settings.negative_margin_block_mode,
            "global_cloud_kill_switch": bool(getattr(settings, "global_cloud_kill_switch", False)),
        },
        "global_usage_today": {
            "global_provider_cost_today_brl": round(global_provider_cost_today_brl, 2),
            "global_cloud_provider_cost_today_brl": round(global_cloud_provider_cost_today_brl, 2),
            "global_request_count_today": global_request_count_today,
            "global_revenue_today_brl": round(global_revenue_today_brl, 2),
            "global_margin_today_brl": round(global_margin_today_brl, 2),
            "global_margin_percent_today": round(global_margin_percent_today, 2),
            "clients_with_negative_margin_count": len(clients_with_negative_margin),
            "providers_over_warning_threshold_count": len(providers_over_warning_threshold),
            "providers_over_block_threshold_count": len(providers_over_block_threshold),
            "clients_over_warning_threshold_count": len(clients_over_warning_threshold),
            "clients_over_block_threshold_count": len(clients_over_block_threshold),
        },
        "providers": providers,
        "clients": clients,
        "warnings": warnings,
        "would_block": would_block,
        "recommendations": recommendations,
        "providers_over_warning_threshold": providers_over_warning_threshold,
        "providers_over_block_threshold": providers_over_block_threshold,
        "clients_over_warning_threshold": clients_over_warning_threshold,
        "clients_over_block_threshold": clients_over_block_threshold,
        "clients_with_negative_margin": clients_with_negative_margin,
    }


async def simulate_commercial_guardrails(
    session: AsyncSession,
    *,
    client_id: str,
    provider: str,
    model: str,
    estimated_cost_brl: float,
    estimated_revenue_brl: float,
) -> dict[str, Any]:
    settings = get_settings()
    now_utc = datetime.now(UTC)
    today_start = _today_start_utc(now_utc)
    try:
        client_identifier: str | UUID = UUID(client_id)
    except ValueError:
        client_identifier = client_id

    stmt_global = select(
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost")
    ).where(RequestFinancial.created_at >= today_start)
    global_cost = float((await session.execute(stmt_global)).scalar() or 0.0)

    stmt_provider = select(
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost")
    ).where(
        RequestFinancial.created_at >= today_start,
        RequestFinancial.provider == provider,
    )
    provider_cost = float((await session.execute(stmt_provider)).scalar() or 0.0)

    stmt_client = select(
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost"),
        func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("revenue"),
        func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
    ).where(
        RequestFinancial.created_at >= today_start,
        RequestFinancial.client_id == client_identifier,
    )
    client_row = (await session.execute(stmt_client)).first()
    client_cost = float(client_row.cost or 0.0)
    client_revenue = float(client_row.revenue or 0.0)
    client_profit = float(client_row.profit or 0.0)

    projected_global_cost = global_cost + estimated_cost_brl
    projected_provider_cost = provider_cost + estimated_cost_brl
    projected_client_cost = client_cost + estimated_cost_brl
    projected_client_revenue = client_revenue + estimated_revenue_brl
    projected_client_margin = client_profit + (estimated_revenue_brl - estimated_cost_brl)
    projected_client_margin_percent = _margin_percent(
        projected_client_margin, projected_client_revenue
    )

    reasons: list[str] = []
    recommendations: list[str] = []

    if getattr(settings, "global_cloud_kill_switch", False) and is_cloud_provider(provider):
        reasons.append("global_cloud_kill_switch")
        recommendations.append(
            "Kill switch global cloud ativo; validar fallback local antes de reabrir providers cloud."
        )

    if (
        settings.max_global_provider_cost_per_day_brl > 0
        and projected_global_cost >= settings.max_global_provider_cost_per_day_brl
    ):
        reasons.append("global_daily_cost_limit_exceeded")
        recommendations.append(
            "Reduzir fallback cloud ou elevar o teto global apenas com aprovação operacional."
        )
    if (
        settings.max_provider_cost_per_day_brl > 0
        and projected_provider_cost >= settings.max_provider_cost_per_day_brl
    ):
        reasons.append("provider_daily_cost_limit_exceeded")
        recommendations.append(
            f"Despriorizar o provider '{provider}' ou revisar sua tabela de preços."
        )
    if (
        settings.max_client_provider_cost_per_day_brl > 0
        and projected_client_cost >= settings.max_client_provider_cost_per_day_brl
    ):
        reasons.append("client_daily_cost_limit_exceeded")
        recommendations.append(
            "Revisar o teto diário por tenant ou ajustar o plano/preço do cliente."
        )
    if projected_client_margin < 0:
        reasons.append("negative_margin")
        recommendations.append(
            "Aumentar receita estimada, reduzir custo estimado ou evitar fallback caro para este cliente."
        )
    elif projected_client_margin_percent < settings.margin_warning_percent:
        recommendations.append(
            "Margem projetada abaixo do threshold de alerta; monitorar antes de habilitar enforcement."
        )

    hard_block_reasons = {
        "global_cloud_kill_switch",
        "global_daily_cost_limit_exceeded",
        "provider_daily_cost_limit_exceeded",
        "client_daily_cost_limit_exceeded",
        "negative_margin",
    }

    return {
        "generated_at_utc": now_utc.isoformat(),
        "mode": _build_mode(settings),
        "client_id": client_id,
        "provider": provider,
        "model": model,
        "allowed_in_report_only": True,
        "would_allow_if_enforced": not any(reason in hard_block_reasons for reason in reasons),
        "estimated_margin_brl": round(estimated_revenue_brl - estimated_cost_brl, 2),
        "estimated_margin_percent": round(
            _margin_percent(estimated_revenue_brl - estimated_cost_brl, estimated_revenue_brl), 2
        ),
        "projected_client_margin_brl": round(projected_client_margin, 2),
        "projected_client_margin_percent": round(projected_client_margin_percent, 2),
        "projected_global_provider_cost_today_brl": round(projected_global_cost, 2),
        "projected_provider_cost_today_brl": round(projected_provider_cost, 2),
        "projected_client_cost_today_brl": round(projected_client_cost, 2),
        "reasons": reasons,
        "recommendations": recommendations,
    }
    try:
        client_identifier: str | UUID = UUID(client_id)
    except ValueError:
        client_identifier = client_id
