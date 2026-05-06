import os
from datetime import datetime, timezone
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
async def health():
    return {"status": "ok", "process": "alive"}


@router.get("/ready", tags=["system"])
async def ready(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    status = "ready"
    dependencies = {"postgres": "ok", "redis": "ok", "migrations": "ok"}
    
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        dependencies["postgres"] = "error"
        status = "not_ready"

    try:
        await redis.ping()
    except Exception:
        dependencies["redis"] = "error"
        status = "not_ready"
        
    try:
        res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        if not res.scalar():
            dependencies["migrations"] = "missing"
            status = "not_ready"
    except Exception:
        dependencies["migrations"] = "error"
        status = "not_ready"

    if status != "ready":
        return Response(
            content=f'{{"status":"{status}","dependencies":{str(dependencies).replace("\'", "\"")}}}',
            media_type="application/json",
            status_code=503
        )
        
    return {"status": "ready", "dependencies": dependencies}


@router.get("/status", tags=["system"])
async def system_status(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
        
    redis_ok = True
    try:
        await redis.ping()
    except Exception:
        redis_ok = False
        
    model_count = 0
    if db_ok:
        try:
            model_count = (await session.execute(select(func.count(ModelRegistry.id)).where(ModelRegistry.is_active.is_(True)))).scalar() or 0
        except Exception:
            pass
            
    dp_health = await proxy.health()
    
    return {
        "status": "ok" if db_ok and redis_ok and dp_health else "degraded",
        "components": {
            "api": "online",
            "database": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline",
            "inference_plane": "online" if dp_health else "offline",
            "models_active": model_count
        }
    }


@router.get("/admin/status", tags=["system"])
async def admin_system_status(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    _=Depends(require_admin),
):
    db_detail = {"ok": False, "latency_ms": 0}
    start = perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        db_detail["ok"] = True
        db_detail["latency_ms"] = round((perf_counter() - start) * 1000, 2)
    except Exception as e:
        db_detail["error"] = str(e)
        
    redis_detail = {"ok": False, "latency_ms": 0}
    start = perf_counter()
    try:
        await redis.ping()
        redis_detail["ok"] = True
        redis_detail["latency_ms"] = round((perf_counter() - start) * 1000, 2)
    except Exception as e:
        redis_detail["error"] = str(e)
        
    job_snapshot = {"error": "database offline"}
    if db_detail["ok"]:
        try:
            job_snapshot = await get_admin_job_snapshot(session, redis)
        except Exception as e:
            job_snapshot = {"error": str(e)}
    
    inference_queues = proxy.queue_manager.get_snapshot()

    backends = []
    models = []
    if db_detail["ok"]:
        try:
            backend_rows = (await session.execute(select(InferenceBackend))).scalars().all()
            for b in backend_rows:
                backends.append(await proxy.health_backend(b))
                
            model_rows = (await session.execute(select(ModelRegistry).where(ModelRegistry.is_active.is_(True)))).scalars().all()
            for m in model_rows:
                models.append({
                    "model_id": m.model_id,
                    "provider": m.provider,
                    "status": m.status,
                    "is_default": m.is_default
                })
        except Exception as e:
            backends = [{"error": str(e)}]
            models = [{"error": str(e)}]

    rag_status = {
        "enabled": settings.rag_enabled,
        "storage_dir": settings.rag_storage_dir if settings.localhost_mode else "masked",
        "storage_ok": os.path.exists(settings.rag_storage_dir),
        "embedding_provider": settings.rag_embedding_provider,
        "vector_mode": "unknown"
    }
    if settings.rag_enabled and db_detail["ok"]:
        try:
            conn = await session.connection()
            res = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            rag_status["vector_mode"] = "pgvector" if res.scalar() else "fallback"
        except Exception:
            rag_status["vector_mode"] = "error"

    cache_info = {
        "response_cache_enabled": settings.response_cache_enabled,
        "semantic_cache_enabled": settings.semantic_cache_enabled,
        "ttl": settings.response_cache_ttl_seconds
    }

    return {
        "status": "ok" if db_detail["ok"] and redis_detail["ok"] else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "postgres": db_detail,
            "redis": redis_detail
        },
        "queues": job_snapshot,
        "inference_queues": inference_queues,
        "inference": {
            "backends": backends,
            "active_models": models
        },
        "rag": rag_status,
        "cache": cache_info
    }


@router.get("/admin/health/deep", tags=["system"])
async def health_deep(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    admin=Depends(require_admin),
):
    await observe_billing_status_metrics(session)
    # We reuse the status logic but can add more if needed
    status = await admin_system_status(session, redis, proxy, admin)
    
    # Add request stats which are specifically in deep health
    request_stats = (
        await session.execute(
            select(
                func.count(RequestLog.id).label("requests_total"),
                func.count().filter(RequestLog.http_status >= 400).label("errors_total"),
                func.avg(RequestLog.latency_ms).label("avg_latency_ms"),
            )
        )
    ).mappings().first()
    
    status["requests"] = {
        "requests_total": int(request_stats["requests_total"] or 0),
        "errors_total": int(request_stats["errors_total"] or 0),
        "avg_latency_ms": round(float(request_stats["avg_latency_ms"] or 0), 2),
    }
    
    return status


@router.get("/metrics", tags=["system"])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/admin-tests", include_in_schema=False)
async def admin_tests():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-tests" / "index.html"
    return FileResponse(static_file)

@router.get("/admin-dashboard", include_in_schema=False)
async def admin_dashboard():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin" / "index.html"
    return FileResponse(static_file)


@router.get("/admin-lab", include_in_schema=False)
async def admin_lab():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-lab" / "index.html"
    return FileResponse(static_file)


@router.get("/monitoring", include_in_schema=False)
async def monitoring_dashboard():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "monitoring" / "index.html"
    return FileResponse(static_file)


@router.get("/client-portal", include_in_schema=False)
async def client_portal():
    static_file = Path(__file__).resolve().parents[1] / "static" / "portal" / "index.html"
    return FileResponse(static_file)
