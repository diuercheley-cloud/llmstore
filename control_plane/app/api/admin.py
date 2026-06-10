# Owner: platform-ops
import json
import os
import uuid
from datetime import date
from pathlib import Path

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.core.request_log import RequestLog
from app.schemas.admin import CapabilityRead
from app.services.auth import require_admin
from app.services.security_monitor import list_security_events
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
settings = get_settings()


@router.get("/capabilities", response_model=list[CapabilityRead])
async def get_capabilities():
    return [
        {
            "feature": "/v1/chat/completions",
            "status": "GA",
            "backend_support": "llama.cpp, ollama, vllm, mock",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/test-chat.sh"
        },
        {
            "feature": "streaming",
            "status": "GA",
            "backend_support": "llama.cpp, ollama, vllm, mock",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/test-stream.sh"
        },
        {
            "feature": "/v1/models",
            "status": "GA",
            "backend_support": "control-plane",
            "production_ready": True,
            "limitations": None,
            "validator_script": None
        },
        {
            "feature": "/v1/embeddings",
            "status": "GA",
            "backend_support": "local-transformers, mock",
            "production_ready": True,
            "limitations": "Local transformer model (sentence-transformers) or mock",
            "validator_script": "scripts/validate-embeddings-local.sh"
        },
        {
            "feature": "/v1/responses",
            "status": "Beta",
            "backend_support": "control-plane-proxy",
            "production_ready": True,
            "limitations": "Streaming ainda não suportado; tools dependem da capability do provider/modelo",
            "validator_script": "scripts/test-responses.sh"
        },
        {
            "feature": "tools/function calling",
            "status": "GA",
            "backend_support": "Native for supported cloud and local backends",
            "production_ready": True,
            "limitations": "Schemas passam por validação e argumentos sensíveis são sanitizados nos logs",
            "validator_script": None
        },
        {
            "feature": "RAG",
            "status": "GA",
            "backend_support": "local-rag-engine",
            "production_ready": True,
            "limitations": "Requer embeddings (mesmo que mock)",
            "validator_script": "scripts/test-rag.sh"
        },
        {
            "feature": "TTS",
            "status": "GA",
            "backend_support": "pocket-tts",
            "production_ready": True,
            "limitations": "Local only",
            "validator_script": "scripts/pocket-tts.sh"
        },
        {
            "feature": "billing manual/local",
            "status": "GA",
            "backend_support": "control-plane",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/run-billing-cycle.sh"
        },
        {
            "feature": "PSP/PIX real",
            "status": "Future",
            "backend_support": "None",
            "production_ready": False,
            "limitations": "Não implementado",
            "validator_script": None
        },
        {
            "feature": "Client Portal",
            "status": "GA",
            "backend_support": "static-frontend",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/ui-health.sh"
        },
        {
            "feature": "Admin Dashboard",
            "status": "GA",
            "backend_support": "static-frontend",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/ui-health.sh"
        },
        {
            "feature": "Admin Lab",
            "status": "GA",
            "backend_support": "static-frontend",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/ui-health.sh"
        },
        {
            "feature": "DR/backup/restore",
            "status": "GA",
            "backend_support": "scripts",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/dr-test-local.sh"
        },
        {
            "feature": "upgrade/rollback",
            "status": "GA",
            "backend_support": "scripts",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/upgrade-test.sh"
        },
        {
            "feature": "tenant export/delete",
            "status": "GA",
            "backend_support": "control-plane",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/export-client-local.sh"
        },
        {
            "feature": "security report",
            "status": "GA",
            "backend_support": "scripts",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/security-report-local.sh"
        },
        {
            "feature": "readiness report",
            "status": "GA",
            "backend_support": "scripts",
            "production_ready": True,
            "limitations": None,
            "validator_script": "scripts/production-readiness-local.sh"
        },
        {
            "feature": "Confidential Computing & Tenant Encryption",
            "status": "GA",
            "backend_support": "AES-256-GCM local envelope encryption",
            "production_ready": True,
            "limitations": "Sem suporte nativo a HSM/KMS externo nesta versão",
            "validator_script": "scripts/validate-tenant-encryption.sh"
        }
    ]


@router.get("/requests")
async def get_requests(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(RequestLog).order_by(desc(RequestLog.created_at)).limit(200))
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "client_id": str(row.client_id),
            "model": row.model,
            "endpoint": row.endpoint,
            "prompt_tokens_estimated": row.prompt_tokens_estimated,
            "completion_tokens_estimated": row.completion_tokens_estimated,
            "latency_ms": row.latency_ms,
            "estimated_cost_usd": float(row.estimated_cost_usd or 0),
            "status": row.http_status,
            "backend_name": row.backend_name,
            "attempts": row.attempts,
            "fallback_used": row.fallback_used,
            "cache_hit": row.cache_hit,
            "tool_call_count": row.tool_call_count,
            "had_tool_call": row.tool_call_count > 0,
            "tool_calls": json.loads(row.tool_calls_json) if row.tool_calls_json else [],
            "backend_errors": json.loads(row.backend_errors_json) if row.backend_errors_json else [],
            "error": row.error_message,
            "correlation_id": row.correlation_id,
            "source_ip": row.source_ip,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/security/events")
async def get_security_events(session: AsyncSession = Depends(get_db_session)):
    return await list_security_events(session)


@router.get("/system/api-surface", response_model=list[dict])
async def get_system_api_surface():
    import yaml
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(current_dir, "../../../config/api-surface.yaml"))
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="API Surface registry config not found.")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading API Surface registry: {str(e)}")
