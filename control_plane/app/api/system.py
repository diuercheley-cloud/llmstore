
# Owner: platform-ops
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, time
from typing import Annotated, Any, Dict

import httpx
from app.api.deps import get_inference_proxy
from app.core.config import Settings, get_settings
from app.services.runtime_dependencies import get_db, get_db_session, get_redis
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_registry import ModelRegistry
from app.services.inference.backend_router import UniversalInferenceRouter
from app.services.auth import require_admin
from app.services.config_service import ConfigService
from app.services.generation_jobs import get_admin_job_snapshot
from app.services.inference_proxy import InferenceProxy
from app.services.security_monitor import observe_billing_status_metrics
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
settings = get_settings()


@router.get("/api/system/profile", tags=["system"])
async def get_system_profile() -> Dict[str, Any]:
    """Return the active operational profile and its capability posture."""
    return ConfigService.get_instance().get_profile_summary()


@router.get("/api/backends/capabilities", tags=["system"])
async def get_backend_capabilities(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    proxy: Annotated[InferenceProxy, Depends(get_inference_proxy)],
) -> dict[str, Any]:
    backends = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    router = UniversalInferenceRouter(proxy)
    reports = [await router.report_for(backend) for backend in backends]
    return {
        "backends": [report.model_dump() for report in reports],
        "summary": {
            "total": len(reports),
            "healthy": sum(1 for report in reports if report.health.get("ok") is True or report.health.get("status") in {"healthy", "degraded"}),
            "streaming": sum(1 for report in reports if report.capabilities.streaming),
            "embeddings": sum(1 for report in reports if report.capabilities.embeddings),
            "tool_calling": sum(1 for report in reports if report.capabilities.tool_calling),
            "vision": sum(1 for report in reports if report.capabilities.vision),
            "batching": sum(1 for report in reports if report.capabilities.batching),
        },
    }


def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def get_git_branch():
    try:
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def _get_latest_artifact_info(base_dir: str, filename: str) -> dict | None:
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
            return {
                "timestamp": reports[0].name,
                "path": str(report_file.relative_to(Path.cwd()))
            }
        # If filename is empty, just return the directory info
        if not filename:
             return {
                "timestamp": reports[0].name,
                "path": str(reports[0].relative_to(Path.cwd()))
            }
    except Exception:
        pass
    return None


def _get_latest_release_info() -> dict | None:
    try:
        release_dir = Path("releases")
        if not release_dir.exists():
            return None
        # Releases are named like v1.5.6-runtime-hardening
        releases = sorted([d for d in release_dir.iterdir() if d.is_dir() and d.name.startswith("v")], reverse=True)
        if not releases:
            return None
        return {
            "version": releases[0].name,
            "path": str(releases[0].relative_to(Path.cwd()))
        }
    except Exception:
        pass
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


@router.get("/operational-readiness", tags=["system"])
async def get_operational_readiness(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict[str, Any]:
    """
    Check operational readiness of the system.
    """
    from sqlalchemy import text
    
    checks = {}
    
    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"failed: {str(e)}"
        
    # 2. Redis check
    try:
        from app.services.runtime_dependencies import redis_client
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"failed: {str(e)}"
        
    # 3. Agentic Readiness check
    agentic_info = {"enabled": settings.agent_runtime_enabled, "status": "disabled"}
    if settings.agent_runtime_enabled:
        try:
            from app.services.agents.agent_readiness import AgentReadinessService
            agent_svc = AgentReadinessService(db)
            agent_report = await agent_svc.check_readiness()
            agentic_info["status"] = agent_report["status"]
            agentic_info["blockers"] = agent_report.get("blockers", [])
            agentic_info["warnings"] = agent_report.get("warnings", [])
            checks["agentic"] = "ok" if agent_report["status"] in ["ready", "degraded", "disabled"] else f"failed: {agent_report['status']}"
        except Exception as e:
            agentic_info["status"] = "error"
            checks["agentic"] = f"error: {str(e)}"
    else:
        checks["agentic"] = "ok"

    # 4. Modes
    checks["modes"] = {
        "rbac": "enabled" if settings.rbac_admin_enabled else "disabled",
        "pki": "enabled" if settings.pki_enabled else "disabled",
        "attestation": settings.attestation_mode,
        "tokenizer": settings.tokenizer_mode,
        "hot_swap": "enabled" if settings.model_hot_swap_enabled else "disabled",
        "agentic": agentic_info,
    }
    
    # 5. Deployment Mode Coherence Check
    try:
        from app.services.platform.deployment_modes import DeploymentModeService
        mode_svc = DeploymentModeService()
        is_coherent, blockers, warnings = mode_svc.validate_coherence(settings)
        checks["deployment_mode"] = {
            "mode": settings.deployment_mode,
            "is_coherent": is_coherent,
            "blockers": blockers,
            "warnings": warnings,
            "governance_posture": mode_svc.get_governance_posture(settings.deployment_mode)
        }
    except Exception as e:
        is_coherent = False
        blockers = [f"Coherence check error: {str(e)}"]
        warnings = []
        checks["deployment_mode"] = {
            "mode": settings.deployment_mode,
            "is_coherent": False,
            "blockers": blockers,
            "warnings": warnings,
            "governance_posture": "Unknown"
        }
    
    # 6. Overall status
    all_ok = all(v == "ok" or v.startswith("ok") for k, v in checks.items() if k not in ("modes", "deployment_mode"))
    all_ok = all_ok and is_coherent and len(blockers) == 0
    status = "pilot_ready" if all_ok else "production_blocked"
    
    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "process": "alive"}


@router.get("/ready", tags=["system"])
async def ready(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    import logging
    status = "ready"
    dependencies = {"postgres": "ok", "redis": "ok", "migrations": "ok"}
    
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logging.error(f"Readiness check failed: postgres dependency not ready. Error: {e}")
        dependencies["postgres"] = "error"
        status = "not_ready"

    try:
        await redis.ping()
    except Exception as e:
        logging.error(f"Readiness check failed: redis dependency not ready. Error: {e}")
        dependencies["redis"] = "error"
        status = "not_ready"
        
    try:
        res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        if not res.scalar():
            logging.error("Readiness check failed: migrations dependency not ready (missing version)")
            dependencies["migrations"] = "missing"
            status = "not_ready"
    except Exception as e:
        logging.error(f"Readiness check failed: migrations dependency not ready. Error: {e}")
        dependencies["migrations"] = "error"
        status = "not_ready"

    settings = get_settings()
    if settings.attestation_mode == "enforcing":
        from app.services.security.attestation_service import NodeAttestationService
        try:
            att_svc = NodeAttestationService(session)
            report = await att_svc.generate_report()
            if not await att_svc.verify_report(report):
                dependencies["attestation"] = "failed"
                status = "not_ready"
            else:
                dependencies["attestation"] = "ok"
        except Exception as e:
            logging.error(f"Readiness attestation failed: {e}")
            dependencies["attestation"] = "error"
            status = "not_ready"

    # Check for opt-in components
    # 1. RAG
    if not settings.rag_enabled:
        dependencies["rag"] = "disabled"
        logging.warning("Readiness degraded reason: RAG component is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["rag"] = "ok"

    # 2. TTS
    if not settings.tts_enabled:
        dependencies["tts"] = "disabled"
        logging.warning("Readiness degraded reason: TTS component is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["tts"] = "ok"

    # 3. LM Studio
    if not settings.lmstudio_enabled:
        dependencies["lmstudio"] = "disabled"
        logging.warning("Readiness degraded reason: LM Studio provider is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["lmstudio"] = "ok"

    # 4. Agentic Runtime
    if not settings.agent_runtime_enabled:
        dependencies["agentic"] = "disabled"
    else:
        try:
            from app.services.agents.agent_readiness import AgentReadinessService
            agent_svc = AgentReadinessService(session)
            agent_report = await agent_svc.check_readiness()
            dependencies["agentic"] = agent_report["status"]
            if agent_report["status"] == "blocked":
                status = "not_ready"
            elif agent_report["status"] == "degraded" and status != "not_ready":
                status = "degraded"
        except Exception as e:
            logging.error(f"Readiness agentic check failed: {e}")
            dependencies["agentic"] = "error"
            status = "not_ready"

    # 5. Deployment Mode Coherence Check
    try:
        from app.services.platform.deployment_modes import DeploymentModeService
        mode_svc = DeploymentModeService()
        is_coherent, blockers, warnings = mode_svc.validate_coherence(settings)
        dependencies["deployment_mode"] = "ok" if is_coherent else "degraded"
        if blockers:
            dependencies["deployment_mode"] = "blocked"
            logging.error(f"Readiness check warning: deployment mode configuration incoherence. Blockers: {blockers}")
        elif warnings:
            if status != "not_ready":
                status = "degraded"
            logging.warning(f"Readiness check warning: deployment mode configuration warning. Warnings: {warnings}")
    except Exception as e:
        logging.error(f"Readiness check failed: deployment mode check failed. Error: {e}")
        dependencies["deployment_mode"] = "error"
        status = "not_ready"

    if status == "not_ready":
        return Response(
            content=f'{{"status":"{status}","dependencies":{json.dumps(dependencies)}}}',
            media_type="application/json",
            status_code=503
        )
        
    return {"status": status, "dependencies": dependencies}


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
        "appliance_mode": settings.local_appliance_mode,
        "cors_configured": bool(settings.cors_allow_origins or settings.localhost_mode or settings.local_appliance_mode),
        "components": {
            "api": "online",
            "database": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline",
            "inference_plane": "online" if dp_health else "offline",
            "models_active": model_count
        }
    }


@router.get("/admin/jobs", tags=["system"])
async def admin_jobs_endpoint(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    _=Depends(require_admin),
):
    return await get_admin_job_snapshot(session, redis)


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
    current_settings = get_settings()
    start_total = perf_counter()
    await observe_billing_status_metrics(session)

    # API and System
    uptime_seconds = round(time() - current_settings.start_time, 2)
    git_commit = get_git_commit()
    appliance_mode = current_settings.local_appliance_mode

    # Database
    db_detail = {"status": "offline", "latency_ms": 0, "migrations_status": "unknown", "ok": False}
    start_db = perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        db_detail["status"] = "online"
        db_detail["ok"] = True
        db_detail["latency_ms"] = round((perf_counter() - start_db) * 1000, 2)
        try:
            res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            db_detail["migrations_status"] = "ok" if res.scalar() else "missing"
        except Exception:
            db_detail["migrations_status"] = "error"
    except Exception as e:
        db_detail["error"] = str(e)

    # Redis
    redis_detail = {"status": "offline", "latency_ms": 0, "ok": False}
    start_redis = perf_counter()
    try:
        await redis.ping()
        redis_detail["status"] = "online"
        redis_detail["ok"] = True
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
            backend_rows = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_active == True))).scalars().all()
            health_results = await asyncio.gather(*[proxy.health_backend(b) for b in backend_rows])
            for b, h in zip(backend_rows, health_results):
                m_count = (await session.execute(
                    select(func.count(ModelRegistry.id)).where(ModelRegistry.inference_backend_id == b.id)
                )).scalar() or 0
                backends.append({
                    "backend_id": str(b.id),
                    "type": b.provider,
                    "status": "online" if h.get("ok") else "offline",
                    "ok": h.get("ok", False),
                    "latency_ms": h.get("latency_ms", 0),
                    "last_error_sanitized": h.get("error") if h.get("error") else None,
                    "model_count": m_count
                })
        except Exception as e:
            backends.append({"error": str(e), "ok": False})

    # Models
    models = []
    if db_detail["status"] == "online":
        try:
            model_rows = (await session.execute(select(ModelRegistry))).scalars().all()
            for m in model_rows:
                file_path = Path(current_settings.models_dir) / m.model_file
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
        "enabled": current_settings.rag_enabled,
        "worker_status": "disabled",
        "storage_status": "ok" if os.path.exists(current_settings.rag_storage_dir) else "error"
    }
    if current_settings.rag_enabled and db_detail["status"] == "online":
        try:
            res = await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            rag_status["worker_status"] = "ready" if res.scalar() else "degraded (no pgvector)"
        except Exception:
            rag_status["worker_status"] = "error"

    # TTS
    tts_status = {"enabled": current_settings.tts_enabled, "service_status": "disabled", "latency_ms": 0}
    if current_settings.tts_enabled:
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
        "mode": current_settings.local_billing_mode,
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
        "check_secrets_available": os.path.exists("scripts/check-secrets.sh"),
        "local_appliance_mode": current_settings.local_appliance_mode,
        "cors_configured": bool(current_settings.cors_allow_origins or current_settings.localhost_mode or current_settings.local_appliance_mode),
        "cors_origins_count": len(current_settings.cors_origins),
        "cors_warnings": current_settings.cors_warnings
    }

    # Providers
    providers_data = []
    try:
        from app.services.providers.registry import (
            get_all_provider_health,
            get_all_provider_statuses,
        )
        provider_health_list = await get_all_provider_health()
        provider_statuses = get_all_provider_statuses()
        status_map = {s.provider_id: s for s in provider_statuses}
        for ph in provider_health_list:
            st = status_map.get(ph.provider_id)
            providers_data.append({
                "provider_id": ph.provider_id,
                "enabled": ph.enabled,
                "configured": ph.configured,
                "healthy": ph.healthy,
                "capabilities": st.capabilities.model_dump() if st else {},
                "last_error_sanitized": ph.last_error_sanitized,
            })
    except Exception as e:
        providers_data = [{"error": "providers check failed", "detail": str(e)}]

    # Readiness Score
    readiness_score = "READY"
    critical_failures = []
    warnings = []

    for w in current_settings.cors_warnings:
        if w["severity"] == "high":
            readiness_score = "READY_WITH_WARNINGS"
        warnings.append(f"CORS: {w['message']}")

    # Security check for admin token
    if current_settings.admin_token == "default-admin-token":
        warnings.append("Insecure default ADMIN_TOKEN in use")
    elif len(current_settings.admin_token) < 32:
        warnings.append("ADMIN_TOKEN is weak (less than 32 characters)")

    if appliance_mode and current_settings.localhost_mode is False:
        warnings.append("Appliance mode enabled but localhost_mode is false")

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
            # We don't mark as DEGRADED if we still have some backends online
            # unless ALL active backends are down
            if dp_ok:
                warnings.append(f"Some inference backends are unreachable: {len(unreachable)}")
            else:
                readiness_score = "DEGRADED"
                critical_failures.append("All inference backends are unreachable")
    else:
        # No backends defined might be a warning or degraded
        if readiness_score == "READY":
            readiness_score = "DEGRADED"
        warnings.append("No inference backends configured")

    if current_settings.tts_enabled and tts_status["service_status"] != "online":
        warnings.append(f"TTS service is {tts_status['service_status']}")

    response = {
        "api": {
            "status": "online",
            "version": current_settings.project_version,
            "git_commit": git_commit,
            "uptime_seconds": uptime_seconds,
            "appliance_mode": appliance_mode,
        },
        "postgres": db_detail,
        "redis": redis_detail,
        "queues": job_snapshot,
        "inference_queues": proxy.queue_manager.get_snapshot(),
        "inference_backends": backends,
        "models": models,
        "providers": providers_data,
        "rag": rag_status,
        "tts": tts_status,
        "billing": billing_status,
        "security": security_info,
        "readiness_score": readiness_score,
        "status": "ok" if readiness_score == "READY" else readiness_score.lower(),
        "warnings": warnings,
        "critical_failures": critical_failures,
        "total_latency_ms": round((perf_counter() - start_total) * 1000, 2)
    }
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


@router.get("/admin/system/control-center", tags=["system"])
async def get_control_center(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    admin=Depends(require_admin),
):
    deep_health = await health_deep(session, redis, proxy, admin)
    
    # Artifacts
    readiness = _get_latest_artifact_info("artifacts/production-readiness", "report.json")
    security = _get_latest_artifact_info("artifacts/security-reports", "security-report.json")
    validation = _get_latest_artifact_info("artifacts/local-production-validation", "report.json")
    if not validation:
        validation = _get_latest_artifact_info("artifacts/validation", "report.json")
    
    demo = _get_latest_artifact_info("artifacts/local-demo", "summary.json")
    release = _get_latest_release_info()
    backup = _get_latest_artifact_info("artifacts/backups-local", "")
    if not backup:
        backup = _get_latest_artifact_info("artifacts/backups", "")
        
    upgrade = _get_latest_artifact_info("artifacts/upgrades", "report.json")
    if not upgrade:
        upgrade = _get_latest_artifact_info("artifacts/post-upgrade-smoke", "report.json")
        
    benchmark = _get_latest_artifact_info("artifacts/model-benchmarks", "summary.json")
    if not benchmark:
        benchmark = _get_latest_artifact_info("artifacts/benchmarks", "summary.json")

    suggested_commands = [
        {"label": "Health", "command": "make health"},
        {"label": "Validate", "command": "make validate"},
        {"label": "Demo", "command": "make demo"},
        {"label": "Security", "command": "make security"},
        {"label": "Readiness", "command": "make readiness"},
        {"label": "Backup", "command": "make backup"},
        {"label": "Smoke", "command": "make smoke"},
        {"label": "Benchmark", "command": "make benchmark"},
    ]

    return {
        "version": settings.project_version,
        "git_commit": get_git_commit(),
        "git_branch": get_git_branch(),
        "uptime": deep_health.get("api", {}).get("uptime_seconds"),
        "readiness_score": deep_health.get("readiness_score"),
        "security_score": deep_health.get("security", {}).get("last_security_report_score"),
        "health_status": deep_health.get("status"),
        "warnings": deep_health.get("warnings", []),
        "critical_failures": deep_health.get("critical_failures", []),
        "artifacts": {
            "readiness": readiness or "not generated yet",
            "security": security or "not generated yet",
            "validation": validation or "not generated yet",
            "demo": demo or "not generated yet",
            "release": release or "not generated yet",
            "backup": backup or "not generated yet",
            "upgrade": upgrade or "not generated yet",
            "benchmark": benchmark or "not generated yet",
        },
        "suggested_commands": suggested_commands
    }


@router.get("/admin/system/reports/latest", tags=["system"])
async def get_latest_reports(admin=Depends(require_admin)):
    return {
        "readiness": _get_latest_artifact_info("artifacts/production-readiness", "report.json"),
        "security": _get_latest_artifact_info("artifacts/security-reports", "security-report.json"),
        "validation": _get_latest_artifact_info("artifacts/local-production-validation", "report.json"),
    }


@router.get("/admin/system/releases/latest", tags=["system"])
async def get_latest_release(admin=Depends(require_admin)):
    return _get_latest_release_info() or {"status": "none"}


@router.get("/admin/system/backups/latest", tags=["system"])
async def get_latest_backup(admin=Depends(require_admin)):
    backup = _get_latest_artifact_info("artifacts/backups-local", "")
    if not backup:
        backup = _get_latest_artifact_info("artifacts/backups", "")
    return backup or {"status": "none"}


@router.get("/admin/system/benchmarks/latest", tags=["system"])
async def get_latest_benchmark(admin=Depends(require_admin)):
    benchmark = _get_latest_artifact_info("artifacts/model-benchmarks", "summary.json")
    if not benchmark:
        benchmark = _get_latest_artifact_info("artifacts/benchmarks", "summary.json")
    return benchmark or {"status": "none"}


@router.get("/metrics", tags=["system"])
async def metrics():
    import logging
    current_settings = get_settings()
    if not getattr(current_settings, "observability_enabled", True):
        logging.warning("Metrics unavailable: observability is disabled in settings")
        return Response(content="metrics unavailable", status_code=503)
    try:
        from app.core.metrics import update_dynamic_backup_metrics
        update_dynamic_backup_metrics()
    except Exception as e:
        logging.error(f"Failed to update dynamic backup metrics: {e}")
    try:
        data = generate_latest()
        return Response(data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logging.error(f"Metrics unavailable: failed to generate prometheus metrics. Error: {e}")
        return Response(content="metrics unavailable", status_code=503)


@router.get("/admin-tests", include_in_schema=False)
async def admin_tests():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-tests" / "index.html"
    return FileResponse(static_file)

@router.get("/hub", include_in_schema=False)
async def frontend_hub():
    static_file = Path(__file__).resolve().parents[1] / "static" / "hub" / "index.html"
    return FileResponse(static_file)

@router.get("/admin-dashboard", include_in_schema=False)
async def admin_dashboard():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-v2" / "index.html"
    return FileResponse(static_file)

@router.get("/admin-dashboard/{rest:path}", include_in_schema=False)
async def admin_dashboard_catch_all(rest: str):
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-v2" / "index.html"
    return FileResponse(static_file)


@router.get("/admin-v2", include_in_schema=False)
async def admin_v2():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin-dashboard")

@router.get("/admin-v2/{rest:path}", include_in_schema=False)
async def admin_v2_catch_all(rest: str):
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/admin-dashboard/{rest}")


@router.get("/admin-lab", include_in_schema=False)
async def admin_lab():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "admin-lab" / "index.html"
    return FileResponse(static_file)


@router.get("/provider-settings", include_in_schema=False)
async def provider_settings_page():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "provider-settings" / "index.html"
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

@router.get("/client-portal/{rest:path}", include_in_schema=False)
async def client_portal_catch_all(rest: str):
    static_file = Path(__file__).resolve().parents[1] / "static" / "portal" / "index.html"
    return FileResponse(static_file)


@router.get("/harness", include_in_schema=False)
async def harness_page():
    static_file = Path(__file__).resolve().parents[1] / "static" / "harness" / "index.html"
    return FileResponse(static_file)


@router.get("/tests", include_in_schema=False)
async def tests_landing_page():
    if settings.public_exposure:
        return Response(content='{"detail":"disabled"}', status_code=404)
    static_file = Path(__file__).resolve().parents[1] / "static" / "tests" / "index.html"
    return FileResponse(static_file)


@router.get("/harness/{rest:path}", include_in_schema=False)
async def harness_page_catch_all(rest: str):
    static_file = Path(__file__).resolve().parents[1] / "static" / "harness" / "index.html"
    return FileResponse(static_file)


@router.get("/{page}.html", include_in_schema=False)
async def portal_html_pages(page: str):
    allowed_pages = {
        "keys",
        "usage",
        "invoices",
        "wallet",
        "rag",
        "playground",
        "models",
        "plans",
        "trust",
        "audit",
        "disputes",
        "examples",
        "index",
        "index.legacy",
    }
    if page in allowed_pages:
        static_file = Path(__file__).resolve().parents[1] / "static" / "portal" / f"{page}.html"
        return FileResponse(static_file)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Page not found")
