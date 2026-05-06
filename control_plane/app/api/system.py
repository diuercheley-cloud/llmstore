import os
from pathlib import Path
from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.models.request_log import RequestLog
from app.services.auth import require_admin
from app.services.generation_jobs import get_admin_job_snapshot
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import serialize_routing_table
from app.services.security_monitor import observe_billing_status_metrics

router = APIRouter()
settings = get_settings()


@router.get("/health", tags=["system"])
async def health(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    """
    Verifica a saúde básica dos componentes (DB, Redis, Data Plane).
    """
    status = {"postgres": False, "redis": False, "data_plane": False}
    try:
        await session.execute(text("SELECT 1"))
        status["postgres"] = True
    except Exception:
        pass
    try:
        status["redis"] = bool(await redis.ping())
    except Exception:
        pass
    backend_rows = (
        await session.execute(select(InferenceBackend).where(InferenceBackend.is_active.is_(True)))
    ).scalars().all()
    if backend_rows:
        results = [await proxy.health_backend(item) for item in backend_rows]
        status["data_plane"] = all(item["ok"] for item in results)
    else:
        status["data_plane"] = await proxy.health()
    overall = "ok" if all(status.values()) else "degraded"
    return {"status": overall, "dependencies": status}


@router.get("/ready", tags=["system"])
async def ready(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    """
    Verifica se o sistema está pronto para receber tráfego de inferência.
    """
    await session.execute(text("SELECT 1"))
    await redis.ping()
    backend_rows = (
        await session.execute(select(InferenceBackend).where(InferenceBackend.is_active.is_(True), InferenceBackend.is_default.is_(True)))
    ).scalars().all()
    if backend_rows:
        backend_results = [await proxy.health_backend(item) for item in backend_rows]
        backend_ok = all(item["ok"] for item in backend_results)
    else:
        backend_ok = await proxy.health()
    if not backend_ok:
        return Response(content='{"status":"not_ready","dependency":"data_plane"}', media_type="application/json", status_code=503)
    
    # RAG Status Check
    rag_status = {
        "enabled": settings.rag_enabled,
        "storage_ok": os.path.exists(settings.rag_storage_dir),
        "embedding_provider": settings.rag_embedding_provider,
        "vector_mode": "fallback",
        "usage_tracking_enabled": True,
        "limits_enabled": True
    }
    
    if settings.rag_enabled:
        conn = await session.connection()
        res = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        if res.scalar():
            rag_status["vector_mode"] = "pgvector"
            
    return {"status": "ready", "rag": rag_status}


@router.get("/metrics", tags=["system"])
async def metrics():
    """
    Expõe métricas no formato Prometheus.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/admin-tests", include_in_schema=False)
async def admin_tests():
    if settings.public_exposure:
        return Response(
            content='{"detail":"admin tests disabled in public exposure mode"}',
            media_type="application/json",
            status_code=404,
        )
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-tests" / "index.html"
    return FileResponse(static_file)

@router.get("/admin-dashboard", include_in_schema=False)
async def admin_dashboard():
    if settings.public_exposure:
        return Response(
            content='{"detail":"admin dashboard disabled in public exposure mode"}',
            media_type="application/json",
            status_code=404,
        )
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin" / "index.html"
    return FileResponse(static_file)


@router.get("/admin-lab", include_in_schema=False)
async def admin_lab():
    if settings.public_exposure:
        return Response(
            content='{"detail":"admin lab disabled in public exposure mode"}',
            media_type="application/json",
            status_code=404,
        )
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-lab" / "index.html"
    return FileResponse(static_file)


@router.get("/monitoring", include_in_schema=False)
async def monitoring_dashboard():
    if settings.public_exposure:
        return Response(
            content='{"detail":"monitoring disabled in public exposure mode"}',
            media_type="application/json",
            status_code=404,
        )
    static_file = Path(__file__).resolve().parents[1] / "static" / "monitoring" / "index.html"
    return FileResponse(static_file)


@router.get("/client-portal", include_in_schema=False)
async def client_portal():
    static_file = Path(__file__).resolve().parents[1] / "static" / "portal" / "index.html"
    return FileResponse(static_file)


@router.get("/admin/health/deep", tags=["system"])
async def health_deep(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    _=Depends(require_admin),
):
    """
    Realiza uma verificação profunda de saúde, incluindo latências e status detalhado de backends.
    Requer token de administrador.
    """
    await observe_billing_status_metrics(session)
    postgres_detail = {"ok": False}
    redis_detail = {"ok": False}
    data_plane_detail = {"ok": False, "backends": []}

    started = perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        postgres_detail = {"ok": True, "latency_ms": round((perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        postgres_detail = {"ok": False, "error": str(exc)}

    started = perf_counter()
    try:
        pong = await redis.ping()
        redis_detail = {"ok": bool(pong), "latency_ms": round((perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        redis_detail = {"ok": False, "error": str(exc)}

    started = perf_counter()
    try:
        backend_rows = (
            await session.execute(select(InferenceBackend).where(InferenceBackend.is_active.is_(True)).order_by(InferenceBackend.created_at.asc()))
        ).scalars().all()
        if backend_rows:
            results = [await proxy.health_backend(item) for item in backend_rows]
            data_plane_ok = all(item["ok"] for item in results)
            data_plane_detail = {
                "ok": data_plane_ok,
                "latency_ms": round((perf_counter() - started) * 1000, 2),
                "backends": results,
            }
        else:
            data_plane_ok = await proxy.health()
            data_plane_detail = {"ok": data_plane_ok, "latency_ms": round((perf_counter() - started) * 1000, 2), "backends": []}
    except Exception as exc:
        data_plane_detail = {"ok": False, "error": str(exc)}

    active_model = (
        await session.execute(
            select(ModelRegistry.model_id, ModelRegistry.model_file, ModelRegistry.status, ModelRegistry.is_active)
            .where(ModelRegistry.is_active.is_(True))
            .order_by(ModelRegistry.updated_at.desc())
            .limit(1)
        )
    ).mappings().first()
    request_stats = (
        await session.execute(
            select(
                func.count(RequestLog.id).label("requests_total"),
                func.count().filter(RequestLog.http_status >= 400).label("errors_total"),
                func.avg(RequestLog.latency_ms).label("avg_latency_ms"),
            )
        )
    ).mappings().first()
    routing_models = (
        await session.execute(
            select(ModelRegistry)
            .options(
                selectinload(ModelRegistry.inference_backend),
                selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
            )
            .where(ModelRegistry.is_active.is_(True))
            .order_by(ModelRegistry.is_default.desc(), ModelRegistry.created_at.asc())
        )
    ).scalars().all()
    routing_summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "disabled": 0}
    routing_rows = []
    for model in routing_models:
        routes = serialize_routing_table(model)
        for route in routes:
            routing_summary[route["state"]] = routing_summary.get(route["state"], 0) + 1
        routing_rows.append(
            {
                "model_id": model.model_id,
                "model_alias": model.model_alias,
                "is_default": model.is_default,
                "routes": routes,
            }
        )

    return {
        "status": "ok" if postgres_detail["ok"] and redis_detail["ok"] and data_plane_detail["ok"] else "degraded",
        "dependencies": {
            "postgres": postgres_detail,
            "redis": redis_detail,
            "data_plane": data_plane_detail,
        },
        "routing": {
            "summary": routing_summary,
            "models": routing_rows,
        },
        "model": dict(active_model) if active_model else None,
        "requests": {
            "requests_total": int(request_stats["requests_total"] or 0),
            "errors_total": int(request_stats["errors_total"] or 0),
            "avg_latency_ms": round(float(request_stats["avg_latency_ms"] or 0), 2),
        },
        "jobs": await get_admin_job_snapshot(session, redis),
    }
