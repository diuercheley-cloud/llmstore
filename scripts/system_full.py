
# Owner: platform-ops
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, time
from typing import Annotated, Any, Dict

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
import httpx
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_inference_proxy
from app.core.config import get_settings, Settings
from app.db.session import get_db_session, get_redis, get_db
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
        from app.db.session import redis_client
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
    
    # 5. Overall status
    all_ok = all(v == "ok" or v.startswith("ok") for k, v in checks.items() if k != "modes")
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

    if not settings.rag_enabled:
        dependencies["rag"] = "disabled"
        logging.warning("Readiness degraded reason: RAG component is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["rag"] = "ok"

    if not settings.tts_enabled:
        dependencies["tts"] = "disabled"
        logging.warning("Readiness degraded reason: TTS component is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["tts"] = "ok"

    if not settings.lmstudio_enabled:
        dependencies["lmstudio"] = "disabled"
        logging.warning("Readiness degraded reason: LM Studio provider is disabled (opt-in provider disabled)")
        if status != "not_ready":
            status = "degraded"
    else:
        dependencies["lmstudio"] = "ok"

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
