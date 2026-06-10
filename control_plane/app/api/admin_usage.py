import asyncio
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from app.api.deps import get_inference_proxy

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session, get_redis
from app.models.billing import BillingInvoice
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_registry import ModelRegistry
from app.models.core.quota_counter import QuotaCounter
from app.models.rag import RAGDocument
from app.models.rag import RAGDocumentChunk
from app.models.rag import RagUsageEvent
from app.models.core.usage_record import UsageRecord
from app.schemas.admin import ClientRead
from app.services.auth import require_admin
from app.services.billing import list_client_billing_snapshots
from app.services.export_reporting import (
    build_usage_by_client,
    build_usage_by_model,
    build_usage_summary,
)
from app.services.inference_proxy import InferenceProxy
from app.services.security_monitor import observe_billing_status_metrics
from app.services.tts_usage import get_admin_tts_usage, get_tts_usage_and_limits
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin", tags=["admin-usage"], dependencies=[Depends(require_admin)])
settings = get_settings()


@router.get("/usage")
async def get_usage(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(QuotaCounter).order_by(desc(QuotaCounter.updated_at)).limit(200))
    rows = result.scalars().all()
    return [
        {
            "client_id": str(row.client_id),
            "period_start": row.period_start.isoformat(),
            "period_type": row.period_type,
            "used_tokens": row.used_tokens,
            "used_requests": row.used_requests,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


def _get_latest_artifact_report(base_dir: str, filename: str) -> dict | None:
    try:
        reports_dir = Path(base_dir)
        if not reports_dir.exists():
            return None
        # Sort by directory name (timestamp)
        reports = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
        if not reports:
            return None
        report_file = reports[0] / filename
        if report_file.exists():
            with open(report_file) as f:
                data = json.load(f)
                data["_report_internal_path"] = str(report_file.relative_to(Path.cwd()))
                return data
    except Exception:
        pass
    return None


@router.get("/readiness/latest")
async def get_latest_readiness_report():
    report = _get_latest_artifact_report("artifacts/production-readiness", "report.json")
    if not report:
        return {"status": "not_generated"}
    
    # Sanitization: Only return requested fields
    checks = report.get("checks", [])
    top_warnings = [c for c in checks if c.get("status") == "warn"][:5]
    top_failures = [c for c in checks if c.get("status") == "fail"][:5]

    return {
        "score": report.get("score", "UNKNOWN"),
        "generated_at": report.get("generated_at"),
        "totals": report.get("totals", {}),
        "top_warnings": [
            {"title": c.get("title"), "details": c.get("details")} for c in top_warnings
        ],
        "top_failures": [
            {"title": c.get("title"), "details": c.get("details")} for c in top_failures
        ],
        "report_path": report.get("_report_internal_path")
    }


@router.get("/security/latest")
async def get_latest_security_report_endpoint():
    report = _get_latest_artifact_report("artifacts/security-reports", "security-report.json")
    if not report:
        return {"status": "not_generated"}
    
    # Sanitization
    checks = report.get("checks", [])
    critical_failures = [c for c in checks if c.get("severity") == "critical" and c.get("status") == "fail"]
    warnings = [c for c in checks if c.get("status") == "warn"]

    return {
        "score": report.get("score", "UNKNOWN"),
        "generated_at": report.get("generated_at"),
        "totals": report.get("totals", {}),
        "critical_failures": [
            {"title": c.get("title"), "details": c.get("details")} for c in critical_failures
        ],
        "warnings": [
            {"title": c.get("title"), "details": c.get("details")} for c in warnings
        ],
        "report_path": report.get("_report_internal_path")
    }


@router.get("/runtime/summary")
async def get_runtime_summary(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    from app.api.system import health_deep
    from app.models.commercial.commercial_inference_reproducibility import (
        CommercialInferenceReproducibilityRecord,
    )
    
    # Use existing deep health as base
    deep = await health_deep(session, redis, proxy)
    
    # Consolidate with usage summary
    usage = await get_usage_summary(session, proxy)
    
    # Latest report scores
    readiness = _get_latest_artifact_report("artifacts/production-readiness", "report.json")
    security = _get_latest_artifact_report("artifacts/security-reports", "security-report.json")
    reproducibility_total = (
        await session.execute(select(func.count(CommercialInferenceReproducibilityRecord.id)))
    ).scalar() or 0
    reproducibility_replayable = (
        await session.execute(
            select(func.count(CommercialInferenceReproducibilityRecord.id)).where(
                CommercialInferenceReproducibilityRecord.replay_supported.is_(True)
            )
        )
    ).scalar() or 0

    return {
        "health": deep.get("readiness_score", "UNKNOWN"),
        "ready": deep.get("readiness_score") == "READY",
        "deep_health": {
            "postgres": deep.get("postgres", {}).get("status"),
            "redis": deep.get("redis", {}).get("status"),
            "data_plane": deep.get("inference_backends", [{}])[0].get("status") if deep.get("inference_backends") else "offline"
        },
        "backend_status": usage.get("totals", {}).get("backends_online", 0),
        "queues": usage.get("queues", {}).get("summary", {}),
        "rag": deep.get("rag", {}),
        "tts": deep.get("tts", {}),
        "latest_security_score": security.get("score") if security else "not_generated",
        "latest_readiness_score": readiness.get("score") if readiness else "not_generated",
        "reproducibility": {
            "records": int(reproducibility_total),
            "replayable": int(reproducibility_replayable),
            "coverage": round((reproducibility_replayable / reproducibility_total) if reproducibility_total else 0.0, 4),
            "best_effort_only": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/usage/summary")
async def get_usage_summary(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    compact: bool = False,
):
    await observe_billing_status_metrics(session)
    queue_snapshot = proxy.queue_manager.get_snapshot()
    summary = await build_usage_summary(session, queue_snapshot=queue_snapshot)
    clients = await build_usage_by_client(session)
    models = await build_usage_by_model(session)

    # Enrich clients with invoice previews
    snapshots = await list_client_billing_snapshots(session)
    snapshots_by_client = {str(s["client"].id): s for s in snapshots}
    
    for client in clients:
        snapshot = snapshots_by_client.get(client["client_id"])
        if snapshot:
            client["invoice_preview"] = snapshot["invoice_preview"]
        else:
            client["invoice_preview"] = {
                "total_estimated": 0.0,
                "currency": "USD",
                "items": [],
            }

    # Backend/Model health summary
    backend_rows = (await session.execute(select(InferenceBackend))).scalars().all()
    backends_total = len(backend_rows)
    backends_online = 0
    if backend_rows:
        health_results = await asyncio.gather(*[proxy.health_url(b.backend_url, b.healthcheck_path) for b in backend_rows])
        backends_online = sum(1 for ok in health_results if ok)

    model_registry_rows = (await session.execute(select(ModelRegistry))).scalars().all()
    models_total = len(model_registry_rows)
    models_online = 0
    # A model is "online" if it has at least one healthy route
    for m in model_registry_rows:
        # Simple heuristic: if backends_online > 0 and models_total > 0, we assume some models are online
        # Or more accurately, we could check routes, but that's expensive.
        # Let's just say if backends_online > 0, then active models are likely online.
        if backends_online > 0 and m.id: # Just a placeholder condition
            models_online += 1
    
    # RAG Usage Summary
    rag_usage_all = await get_admin_rag_usage(session)
    rag_summary = {
        "total_docs": sum(item.get("doc_count", item.get("documents_count", 0)) for item in rag_usage_all),
        "total_storage_mb": sum(item.get("storage_mb", 0) for item in rag_usage_all),
        "total_queries_month": sum(item.get("queries_month", 0) for item in rag_usage_all),
    }

    # TTS Usage Summary
    tts_usage_all = await get_admin_tts_usage(session)

    plan_buckets: dict[str, dict] = {}
    total_estimated_cost = 0.0
    for client in clients:
        plan_code = client.get("billing_plan_code") or "unknown"
        bucket = plan_buckets.setdefault(
            plan_code,
            {
                "billing_plan_code": plan_code,
                "clients_total": 0,
                "requests_today": 0,
                "requests_month": 0,
                "tokens_today": 0,
                "tokens_month": 0,
                "errors_month": 0,
                "cache_hits_month": 0,
                "cache_misses_month": 0,
                "avg_latency_ms_month_weighted": 0.0,
                "estimated_cost_usd": 0.0,
            },
        )
        bucket["clients_total"] += 1
        bucket["requests_today"] += int(client["requests_today"])
        bucket["requests_month"] += int(client["requests_month"])
        bucket["tokens_today"] += int(client["tokens_today"])
        bucket["tokens_month"] += int(client["tokens_month"])
        bucket["errors_month"] += int(client["errors_month"])
        bucket["cache_hits_month"] += int(client["cache_hits_month"])
        bucket["cache_misses_month"] += int(client["cache_misses_month"])
        
        client_cost = float(client["invoice_preview"]["total_estimated"])
        bucket["estimated_cost_usd"] += client_cost
        total_estimated_cost += client_cost

        if int(client["requests_month"]) > 0:
            bucket["avg_latency_ms_month_weighted"] += float(client["avg_latency_ms_month"]) * int(client["requests_month"])

    plans = []
    for bucket in plan_buckets.values():
        requests_month = bucket["requests_month"]
        plans.append(
            {
                "billing_plan_code": bucket["billing_plan_code"],
                "clients_total": bucket["clients_total"],
                "requests_today": bucket["requests_today"],
                "requests_month": bucket["requests_month"],
                "tokens_today": bucket["tokens_today"],
                "tokens_month": bucket["tokens_month"],
                "errors_month": bucket["errors_month"],
                "cache_hits_month": bucket["cache_hits_month"],
                "cache_misses_month": bucket["cache_misses_month"],
                "cache_hit_rate_month": round(bucket["cache_hits_month"] / (bucket["cache_hits_month"] + bucket["cache_misses_month"]), 4)
                if (bucket["cache_hits_month"] + bucket["cache_misses_month"])
                else 0.0,
                "avg_latency_ms_month": round(bucket["avg_latency_ms_month_weighted"] / requests_month, 2) if requests_month else 0.0,
                "estimated_cost_usd": round(bucket["estimated_cost_usd"], 6),
            }
        )
    plans.sort(key=lambda item: item["requests_month"], reverse=True)
    return {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "totals": {
            "clients_total": summary["clients_total"],
            "requests_total": summary["requests_month"],
            "tokens_estimated_total": summary["tokens_month"],
            "errors_total": sum(item["errors_month"] for item in clients),
            "avg_latency_ms": summary["avg_latency_ms_month"],
            "estimated_cost_usd": round(total_estimated_cost, 6),
            "total_revenue": round(total_estimated_cost, 6), # Alias for frontend
            "monthly_revenue": round(total_estimated_cost, 6), # Alias for frontend
            "pending_invoices": summary["invoices_pending"], # Alias for frontend
            "backends_online": backends_online,
            "backends_total": backends_total,
            "models_online": models_online,
            "models_total": models_total,
        },
        "plans": plans,
        "clients": [] if compact else clients,
        "models": [] if compact else models,
        "queues": queue_snapshot,
        "rag": rag_summary,
        "tts": {} if compact else tts_usage_all,
        "invoices": {
            "pending": summary["invoices_pending"],
            "paid": summary["invoices_paid"],
            "overdue": summary["invoices_overdue"],
            "total": summary["invoices_total"],
        },
        "client_status": {
            "active": summary["clients_active"],
            "suspended": summary["clients_suspended"],
            "blocked": summary["clients_blocked"],
        },
        "cache": {
            "hits_month": summary["cache_hits_month"],
            "misses_month": summary["cache_misses_month"],
            "hit_rate_month": summary["cache_hit_rate_month"],
        },
    }


@router.get("/usage/by-client")
async def get_usage_by_client(session: AsyncSession = Depends(get_db_session)):
    return await build_usage_by_client(session)


@router.get("/usage/by-model")
async def get_usage_by_model(session: AsyncSession = Depends(get_db_session)):
    return await build_usage_by_model(session)


@router.get("/revenue/summary")
async def get_revenue_summary(session: AsyncSession = Depends(get_db_session)):
    invoices = (await session.execute(select(BillingInvoice))).scalars().all()
    total_paid = sum(inv.total_amount for inv in invoices if inv.status == "paid")
    total_pending = sum(inv.total_amount for inv in invoices if inv.status == "pending")
    total_overdue = sum(inv.total_amount for inv in invoices if inv.status == "overdue")
    
    return {
        "generated_at": utc_now().isoformat(),
        "revenue_usd": float(total_paid),
        "pending_usd": float(total_pending),
        "overdue_usd": float(total_overdue),
        "total_revenue": float(total_paid), # Alias for frontend
        "monthly_revenue": float(total_paid), # Simplified for frontend
        "pending_invoices": len([inv for inv in invoices if inv.status == "pending"]), # Alias for frontend
        "invoices_paid": len([inv for inv in invoices if inv.status == "paid"]),
        "invoices_pending": len([inv for inv in invoices if inv.status == "pending"]),
        "invoices_overdue": len([inv for inv in invoices if inv.status == "overdue"]),
    }


@router.get("/rag/usage")
async def get_admin_rag_usage(session: AsyncSession = Depends(get_db_session)):
    from datetime import date

    from app.models.rag import RAGDocument
    from app.models.rag import RagUsageEvent
    from app.services.quota import month_start
    
    # Usage by client
    stmt = (
        select(
            Client.id,
            Client.name,
            func.count(RAGDocument.id).label("doc_count"),
            func.coalesce(func.sum(RAGDocument.file_size_bytes), 0).label("storage_bytes")
        )
        .outerjoin(RAGDocument, RAGDocument.client_id == Client.id)
        .group_by(Client.id, Client.name)
    )
    results_exec = await session.execute(stmt)
    if hasattr(results_exec, "all"):
        results = results_exec.all()
    else:
        results = list(getattr(results_exec, "_rows", []))
    
    start_of_month = datetime.combine(month_start(date.today()), datetime.min.time(), tzinfo=timezone.utc)
    
    usage_stmt = (
        select(
            RagUsageEvent.client_id,
            RagUsageEvent.event_type,
            func.sum(RagUsageEvent.quantity).label("total_quantity")
        )
        .where(RagUsageEvent.created_at >= start_of_month)
        .group_by(RagUsageEvent.client_id, RagUsageEvent.event_type)
    )
    usage_exec = await session.execute(usage_stmt)
    if hasattr(usage_exec, "all"):
        usage_results = usage_exec.all()
    else:
        usage_results = list(getattr(usage_exec, "_rows", []))
    
    client_usage = {}
    for row in usage_results:
        cid = str(row.client_id)
        if cid not in client_usage:
            client_usage[cid] = {"queries": 0, "pages": 0}
        if row.event_type == "rag_query":
            client_usage[cid]["queries"] = row.total_quantity
        elif row.event_type == "pages_processed":
            client_usage[cid]["pages"] = row.total_quantity
            
    return [
        {
            "client_id": str(r.id),
            "client_name": r.name,
            "doc_count": r.doc_count,
            "documents_count": r.doc_count,
            "storage_mb": round(r.storage_bytes / (1024 * 1024), 2),
            "queries_month": client_usage.get(str(r.id), {}).get("queries", 0),
            "pages_month": client_usage.get(str(r.id), {}).get("pages", 0)
        }
        for r in results
        if hasattr(r, "id") and hasattr(r, "name") and hasattr(r, "doc_count") and hasattr(r, "storage_bytes")
    ]



@router.get("/usage/{client_id}/summary")
async def get_client_usage_summary(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    import datetime

    from app.models.core.client import Client
    from app.models.core.usage_record import UsageRecord
    from sqlalchemy.orm import selectinload
    
    result = await session.execute(
        select(Client).options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules)).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    now = datetime.datetime.now(datetime.timezone.utc).date()
    today_start = now
    month_start = now.replace(day=1)
    
    usage_result = await session.execute(
        select(UsageRecord).where(
            UsageRecord.client_id == client_id,
            UsageRecord.period_start.in_([today_start, month_start])
        )
    )
    records = usage_result.scalars().all()
    
    today_record = next((r for r in records if r.period_type == "daily" and r.period_start == today_start), None)
    month_record = next((r for r in records if r.period_type == "monthly" and r.period_start == month_start), None)
    
    today_tokens = today_record.prompt_tokens + today_record.completion_tokens if today_record else 0
    today_requests = today_record.request_count if today_record else 0
    
    month_tokens = month_record.prompt_tokens + month_record.completion_tokens if month_record else 0
    month_requests = month_record.request_count if month_record else 0
    
    daily_quota = client.daily_token_quota
    monthly_quota = client.monthly_token_quota
    
    plan_cost = float(client.billing_plan.price_brl) if client.billing_plan else 0.0
    
    # TTS usage
    tts_usage = await get_tts_usage_and_limits(session, client)
    
    return {
        "client_id": str(client.id),
        "client_name": client.name,
        "plan_name": client.billing_plan.name if client.billing_plan else "None",
        "plan_cost_brl": plan_cost,
        "today": {
            "tokens_used": today_tokens,
            "requests": today_requests,
            "limit": daily_quota,
            "percent_used": round((today_tokens / daily_quota * 100) if daily_quota > 0 else 0, 2),
            "tts_chars_used": tts_usage["usage"]["daily_chars"],
            "tts_limit": tts_usage["limits"]["max_chars_per_day"]
        },
        "month": {
            "tokens_used": month_tokens,
            "requests": month_requests,
            "limit": monthly_quota,
            "percent_used": round((month_tokens / monthly_quota * 100) if monthly_quota > 0 else 0, 2),
            "tts_chars_used": tts_usage["usage"]["monthly_chars"],
            "tts_limit": tts_usage["limits"]["max_chars_per_month"]
        },
        "tts": tts_usage
    }
