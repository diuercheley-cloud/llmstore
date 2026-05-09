import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, time

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
import httpx
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.inference_backend import InferenceBackend
from app.models.model_registry import ModelRegistry
from app.models.request_log import RequestLog
from app.services.auth import require_admin
from app.services.generation_jobs import get_admin_job_snapshot
from app.services.inference_proxy import InferenceProxy
from app.services.security_monitor import observe_billing_status_metrics

router = APIRouter()
settings = get_settings()


def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def get_latest_security_report():
    try:
        reports_dir = Path("artifacts/security-reports")
        if not reports_dir.exists():
            return None
        # Sort by directory name (timestamp)
        reports = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
        if not reports:
            return None
        report_file = reports[0] / "security-report.json"
        if report_file.exists():
            with open(report_file) as f:
                return json.load(f)
    except Exception:
        pass
    return None


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
            content=f'{{"status":"{status}","dependencies":{json.dumps(dependencies)}}}',
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
    
    start = perf_counter()
    dp_ok = await proxy.health()
    dp_latency = round((perf_counter() - start) * 1000, 2)

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
        "status": "ok" if db_detail["ok"] and redis_detail["ok"] and dp_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "postgres": db_detail,
            "redis": redis_detail,
            "data_plane": {"ok": dp_ok, "latency_ms": dp_latency}
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
    start_total = perf_counter()
    await observe_billing_status_metrics(session)

    # API and System
    uptime_seconds = round(time() - settings.start_time, 2)
    git_commit = get_git_commit()

    # Database
    db_detail = {"status": "offline", "latency_ms": 0, "migrations_status": "unknown"}
    start_db = perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        db_detail["status"] = "online"
        db_detail["latency_ms"] = round((perf_counter() - start_db) * 1000, 2)
        try:
            res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            db_detail["migrations_status"] = "ok" if res.scalar() else "missing"
        except Exception:
            db_detail["migrations_status"] = "error"
    except Exception as e:
        db_detail["error"] = str(e)

    # Redis
    redis_detail = {"status": "offline", "latency_ms": 0}
    start_redis = perf_counter()
    try:
        await redis.ping()
        redis_detail["status"] = "online"
        redis_detail["latency_ms"] = round((perf_counter() - start_redis) * 1000, 2)
    except Exception as e:
        redis_detail["error"] = str(e)

    # Queues
    job_snapshot = {"status": "unknown", "waiting": 0, "active": 0, "failed": 0, "delayed": 0}
    if db_detail["status"] == "online":
        try:
            admin_snapshot = await get_admin_job_snapshot(session, redis)
            summary = admin_snapshot.get("summary", {})
            job_snapshot = {
                "status": "ok",
                "waiting": summary.get("queued", 0),
                "active": summary.get("running", 0),
                "failed": summary.get("failed", 0),
                "delayed": summary.get("delayed", 0), # Note: GenerationJob model might not have delayed, but schema expects it
            }
        except Exception as e:
            job_snapshot["status"] = "error"
            job_snapshot["error"] = str(e)

    # Inference Backends
    backends = []
    if db_detail["status"] == "online":
        try:
            backend_rows = (await session.execute(select(InferenceBackend))).scalars().all()
            for b in backend_rows:
                h = await proxy.health_backend(b)
                m_count = (await session.execute(
                    select(func.count(ModelRegistry.id)).where(ModelRegistry.inference_backend_id == b.id)
                )).scalar() or 0
                backends.append({
                    "backend_id": str(b.id),
                    "type": b.provider,
                    "status": "online" if h.get("ok") else "offline",
                    "latency_ms": h.get("latency_ms", 0),
                    "last_error_sanitized": h.get("error") if h.get("error") else None,
                    "model_count": m_count
                })
        except Exception as e:
            backends.append({"error": str(e)})

    # Models
    models = []
    if db_detail["status"] == "online":
        try:
            model_rows = (await session.execute(select(ModelRegistry))).scalars().all()
            for m in model_rows:
                file_path = Path(settings.models_dir) / m.model_file
                exists = file_path.exists()
                size = file_path.stat().st_size if exists else 0
                
                b_status = "unknown"
                if m.inference_backend_id:
                    for b in backends:
                        if b.get("backend_id") == str(m.inference_backend_id):
                            b_status = b.get("status")
                            break

                models.append({
                    "model_id": m.model_id,
                    "alias": m.model_alias,
                    "enabled": m.is_active,
                    "backend_status": b_status,
                    "file_exists": exists,
                    "file_size_bytes": size,
                })
        except Exception:
            pass

    # RAG
    rag_status = {
        "enabled": settings.rag_enabled,
        "worker_status": "disabled",
        "storage_status": "ok" if os.path.exists(settings.rag_storage_dir) else "error"
    }
    if settings.rag_enabled and db_detail["status"] == "online":
        try:
            res = await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            rag_status["worker_status"] = "ready" if res.scalar() else "degraded (no pgvector)"
        except Exception:
            rag_status["worker_status"] = "error"

    # TTS
    tts_status = {"enabled": settings.tts_enabled, "service_status": "disabled", "latency_ms": 0}
    if settings.tts_enabled:
        POCKET_TTS_URL = "http://pocket-tts:8000"
        t_start = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                t_resp = await client.get(f"{POCKET_TTS_URL}/health")
                tts_status["service_status"] = "online" if t_resp.status_code == 200 else "offline"
                tts_status["latency_ms"] = round((perf_counter() - t_start) * 1000, 2)
        except Exception:
            tts_status["service_status"] = "unreachable"
            tts_status["latency_ms"] = round((perf_counter() - t_start) * 1000, 2)

    # Billing
    billing_status = {
        "mode": settings.local_billing_mode,
        "overdue_count": 0,
        "suspended_clients_count": 0
    }
    if db_detail["status"] == "online":
        try:
            rows = (await session.execute(
                select(Client.billing_status, func.count(Client.id)).group_by(Client.billing_status)
            )).all()
            for s_name, total in rows:
                if s_name == "past_due":
                    billing_status["overdue_count"] = int(total or 0)
                elif s_name == "suspended":
                    billing_status["suspended_clients_count"] = int(total or 0)
            
            # Count clients with is_blocked=True as well
            blocked_count = (await session.execute(
                select(func.count(Client.id)).where(Client.is_blocked.is_(True))
            )).scalar() or 0
            if blocked_count > billing_status["suspended_clients_count"]:
                billing_status["suspended_clients_count"] = int(blocked_count)
        except Exception:
            pass

    # Security
    sec_report = get_latest_security_report()
    security_info = {
        "last_security_report_score": sec_report.get("score") if sec_report else "N/A",
        "check_secrets_available": os.path.exists("scripts/check-secrets.sh")
    }

    # Readiness Score
    readiness_score = "READY"
    critical_failures = []
    warnings = []

    if db_detail["status"] != "online":
        readiness_score = "NOT_READY"
        critical_failures.append("Postgres offline")
    
    if redis_detail["status"] != "online":
        readiness_score = "NOT_READY"
        critical_failures.append("Redis offline")

    if db_detail["migrations_status"] != "ok":
        readiness_score = "NOT_READY"
        critical_failures.append(f"Migrations status: {db_detail['migrations_status']}")

    dp_ok = False
    if backends:
        unreachable = [b["backend_id"] for b in backends if b["status"] != "online"]
        dp_ok = len(unreachable) < len(backends)
        if unreachable:
            if readiness_score == "READY":
                readiness_score = "DEGRADED"
            warnings.append(f"Unreachable inference backends: {len(unreachable)}")
    else:
        # No backends defined might be a warning or degraded
        if readiness_score == "READY":
            readiness_score = "DEGRADED"
        warnings.append("No inference backends configured")

    if settings.tts_enabled and tts_status["service_status"] != "online":
        warnings.append(f"TTS service is {tts_status['service_status']}")

    response = {
        "api": {
            "status": "online",
            "version": settings.project_version,
            "git_commit": git_commit,
            "uptime_seconds": uptime_seconds,
        },
        "postgres": db_detail,
        "redis": redis_detail,
        "queues": job_snapshot,
        "inference_backends": backends,
        "models": models,
        "rag": rag_status,
        "tts": tts_status,
        "billing": billing_status,
        "security": security_info,
        "readiness_score": readiness_score,
        "warnings": warnings,
        "critical_failures": critical_failures,
        "total_latency_ms": round((perf_counter() - start_total) * 1000, 2)
    }
    response["status"] = response["readiness_score"]
    response["dependencies"] = {
        "postgres": response["postgres"],
        "redis": response["redis"],
        "queues": response["queues"],
        "data_plane": {
            "ok": dp_ok,
            "latency_ms": next(
                (backend.get("latency_ms", 0) for backend in response["inference_backends"] if "latency_ms" in backend),
                0,
            ),
            "backends": response["inference_backends"],
        },
        "tts": response["tts"],
        "rag": response["rag"],
    }
    return response


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
