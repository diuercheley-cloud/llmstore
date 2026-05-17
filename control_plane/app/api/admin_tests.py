import uuid
import psutil
import subprocess
import shutil
import os
import time
import json
import asyncio
import httpx
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import sqlalchemy as sa
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.db.session import get_db_session, get_redis
from app.services.auth import require_admin_role, AdminRole, admin_key_scheme, get_admin_role
from app.models.client import Client
from app.models.api_key import ApiKey
from app.models.quota_counter import QuotaCounter
from app.models.billing_plan import BillingPlan
from app.models.admin_action_log import AdminActionLog
from app.models.user_quota_override import UserQuotaOverride
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.models.inference_backend import InferenceBackend
from app.models.model_registry import ModelRegistry
from app.models.model_backend_route import ModelBackendRoute
from app.services.embeddings import get_embedding_service
from app.core.time import utc_now
from app.core.config import get_settings
from app.core.security import verify_secret
from pydantic import BaseModel

from app.services.rag_usage import get_rag_usage_and_limits

router = APIRouter(prefix="/admin/tests", tags=["admin_tests"])

@router.get("/rag/status")
async def get_rag_status(
    session: AsyncSession = Depends(get_db_session),
    admin_role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    settings = get_settings()
    
    # Check storage
    storage_ok = os.path.exists(settings.rag_storage_dir)
    storage_count = 0
    if storage_ok:
        storage_count = len(os.listdir(settings.rag_storage_dir))
        
    # Check database
    doc_count = await session.execute(select(func.count(RAGDocument.id)))
    chunk_count = await session.execute(select(func.count(RAGDocumentChunk.id)))
    
    # Check embedding provider
    embedding_ok = False
    embedding_error = None
    try:
        service = get_embedding_service()
        # Test with a small sentence
        await service.embed_text("test")
        embedding_ok = True
    except Exception as e:
        embedding_error = str(e)
        
    # Check pgvector
    conn = await session.connection()
    res = await conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    has_pgvector = res.scalar() is not None
    
    # Get last jobs
    last_docs = (await session.execute(
        select(RAGDocument).order_by(desc(RAGDocument.created_at)).limit(5)
    )).scalars().all()
    
    return {
        "enabled": settings.rag_enabled,
        "limits_enabled": True,
        "usage_tracking_enabled": True,
        "storage": {
            "path": settings.rag_storage_dir,
            "exists": storage_ok,
            "file_count": storage_count
        },
        "database": {
            "document_count": doc_count.scalar(),
            "chunk_count": chunk_count.scalar(),
            "has_pgvector": has_pgvector
        },
        "embeddings": {
            "provider": settings.rag_embedding_provider,
            "model": settings.rag_embedding_model,
            "working": embedding_ok,
            "error": embedding_error
        },
        "last_documents": [
            {
                "id": str(d.id),
                "filename": d.original_filename,
                "status": d.status,
                "created_at": d.created_at.isoformat()
            }
            for d in last_docs
        ]
    }

@router.get("/rag/clients/{client_id}/usage")
async def get_client_rag_usage(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin_role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return await get_rag_usage_and_limits(session, client)

class BlockRagRequest(BaseModel):
    reason: str = "Excessive usage"

@router.post("/rag/clients/{client_id}/block")
async def block_client_rag(
    client_id: uuid.UUID,
    payload: BlockRagRequest,
    request: Request,
    admin_token: str = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
    admin_role: AdminRole = Depends(require_admin_role(AdminRole.SUPER))
):
    from app.models.client_feature_block import ClientFeatureBlock
    
    block = (await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag"
        )
    )).scalar_one_or_none()
    
    if not block:
        block = ClientFeatureBlock(client_id=client_id, feature="rag")
        session.add(block)
    
    block.blocked = True
    block.reason = payload.reason
    block.updated_by_role = admin_role.value
    
    await audit_action(session, "rag_block", request, admin_token, str(client_id), payload.model_dump(), {"blocked": True}, "success")
    await session.commit()
    
    return {"client_id": str(client_id), "feature": "rag", "blocked": True, "reason": payload.reason}

@router.post("/rag/clients/{client_id}/unblock")
async def unblock_client_rag(
    client_id: uuid.UUID,
    request: Request,
    admin_token: str = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
    admin_role: AdminRole = Depends(require_admin_role(AdminRole.SUPER))
):
    from app.models.client_feature_block import ClientFeatureBlock
    
    block = (await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag"
        )
    )).scalar_one_or_none()
    
    if block:
        block.blocked = False
        block.updated_by_role = admin_role.value
        
    await audit_action(session, "rag_unblock", request, admin_token, str(client_id), None, {"blocked": False}, "success")
    await session.commit()
    
    return {"client_id": str(client_id), "feature": "rag", "blocked": False}


async def admin_rate_limit(request: Request, redis: Redis = Depends(get_redis), admin_token: str = Depends(admin_key_scheme)):
    settings = get_settings()
    if not settings.admin_tests_rate_limit_enabled:
        return
    
    role = get_admin_role(admin_token)
    if not role:
        return
        
    limit = 120
    if role == AdminRole.SUPER:
        limit = 30
    elif role == AdminRole.WRITE:
        limit = 60
        
    ip = getattr(request.state, "source_ip", "unknown")
    current_minute = int(time.time() // 60)
    key = f"ratelimit:admin:{role.value}:{ip}:{request.url.path}:{current_minute}"
    
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
        
    if current > limit:
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "rate_limited",
                "retryAfterSeconds": 60 - (int(time.time()) % 60)
            },
            headers={"Retry-After": str(60 - (int(time.time()) % 60))}
        )

async def audit_action(session: AsyncSession, action: str, request: Request, admin_token: str, target_user_id: str | None, payload: dict | None, result: dict | None, status: str):
    role = get_admin_role(admin_token)
    role_str = role.value if role else "unknown"
    ip = getattr(request.state, "source_ip", "unknown")
    user_agent = request.headers.get("user-agent", "unknown")
    
    log = AdminActionLog(
        action=action,
        admin_role=role_str,
        target_user_id=target_user_id,
        request_path=request.url.path,
        request_method=request.method,
        ip_address=ip,
        user_agent=user_agent,
        payload_json=payload,
        result_json=result,
        status=status
    )
    session.add(log)
    # We don't commit here, let the caller commit if it's part of transaction, 
    # but since some might fail, maybe we should commit immediately.
    # We will let the caller commit to ensure atomicity, or we can use a separate session.
    # For simplicity, we just add it to the session.

@router.get("/auth/whoami", dependencies=[Depends(admin_rate_limit)])
async def auth_whoami(admin_token: str = Depends(admin_key_scheme)):
    role = get_admin_role(admin_token)
    if not role:
        raise HTTPException(status_code=401, detail="invalid admin token")
    return {
        "authenticated": True,
        "role": role.value
    }

@router.get("/audit", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def get_audit_log(limit: int = 50, session: AsyncSession = Depends(get_db_session)):
    limit = min(limit, 200)
    query = await session.execute(select(AdminActionLog).order_by(desc(AdminActionLog.created_at)).limit(limit))
    logs = query.scalars().all()
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "admin_role": log.admin_role,
            "target_user_id": log.target_user_id,
            "status": log.status,
            "created_at": log.created_at.isoformat(),
            "request_path": log.request_path
        }
        for log in logs
    ]

@router.get("/users/{user_id}", dependencies=[Depends(require_admin_role(AdminRole.READ)), Depends(admin_rate_limit)])
async def get_user_status(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
        
    plan = None
    if client.billing_plan_id:
        plan = await session.get(BillingPlan, client.billing_plan_id)
        
    plan_daily_quota = plan.daily_token_quota if plan else client.daily_token_quota
    plan_monthly_quota = plan.monthly_token_quota if plan else client.monthly_token_quota
    
    override = await session.get(UserQuotaOverride, user_id)
    
    daily_quota = override.daily_quota_override if override and override.daily_quota_override is not None else plan_daily_quota
    monthly_quota = override.monthly_quota_override if override and override.monthly_quota_override is not None else plan_monthly_quota
    
    # Get current usage
    usage_query = await session.execute(select(QuotaCounter).where(QuotaCounter.client_id == user_id))
    usages = usage_query.scalars().all()
    
    daily_used = next((u.used_tokens for u in usages if u.period_type == "daily"), 0)
    monthly_used = next((u.used_tokens for u in usages if u.period_type == "monthly"), 0)
    
    return {
        "exists": True,
        "id": str(client.id),
        "name": client.name,
        "status": client.billing_status,
        "blocked": client.is_blocked,
        "block_reason": "Admin action" if client.is_blocked else None,
        "quota": {
            "billingPlanDaily": plan_daily_quota,
            "billingPlanMonthly": plan_monthly_quota,
            "effectiveDailyLimit": daily_quota,
            "effectiveMonthlyLimit": monthly_quota,
            "daily_used": daily_used,
            "daily_remaining": max(0, daily_quota - daily_used),
            "monthly_used": monthly_used,
            "monthly_remaining": max(0, monthly_quota - monthly_used),
            "override": {
                "enabled": override is not None,
                "daily_override": override.daily_quota_override if override else None,
                "monthly_override": override.monthly_quota_override if override else None,
                "reason": override.reason if override else None,
                "updated_at": override.updated_at.isoformat() if override else None
            }
        }
    }

@router.post("/users/{user_id}/block", dependencies=[Depends(require_admin_role(AdminRole.SUPER)), Depends(admin_rate_limit)])
async def block_user(user_id: uuid.UUID, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
    
    before_status = client.is_blocked
    if not client.is_blocked:
        client.is_blocked = True
        client.updated_at = utc_now()
        
    await audit_action(session, "user_block", request, admin_token, str(user_id), None, {"was_blocked_before": before_status, "is_blocked_now": client.is_blocked}, "success")
    await session.commit()
    return await get_user_status(user_id, session)

@router.post("/users/{user_id}/unblock", dependencies=[Depends(require_admin_role(AdminRole.SUPER)), Depends(admin_rate_limit)])
async def unblock_user(user_id: uuid.UUID, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
        
    before_status = client.is_blocked
    if client.is_blocked:
        client.is_blocked = False
        client.updated_at = utc_now()
        
    await audit_action(session, "user_unblock", request, admin_token, str(user_id), None, {"was_blocked_before": before_status, "is_blocked_now": client.is_blocked}, "success")
    await session.commit()
    return await get_user_status(user_id, session)

@router.post("/users/{user_id}/quota/reset", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def reset_user_quota(user_id: uuid.UUID, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
        
    await session.execute(update(QuotaCounter).where(QuotaCounter.client_id == user_id).values(used_tokens=0))
    
    result = await get_user_status(user_id, session)
    await audit_action(session, "quota_reset", request, admin_token, str(user_id), None, {"status": "success"}, "success")
    await session.commit()
    
    return result

@router.post("/users/{user_id}/quota/renew", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def renew_user_quota(user_id: uuid.UUID, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
        
    await session.execute(update(QuotaCounter).where(QuotaCounter.client_id == user_id).values(used_tokens=0))
    
    result = await get_user_status(user_id, session)
    await audit_action(session, "quota_renew", request, admin_token, str(user_id), None, {"status": "success"}, "success")
    await session.commit()
    
    return result

class QuotaSetRequest(BaseModel):
    daily_quota: int | None = None
    monthly_quota: int | None = None
    reason: str | None = None

@router.post("/users/{user_id}/quota/set", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def set_user_quota(user_id: uuid.UUID, payload: QuotaSetRequest, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
    
    if (payload.daily_quota is not None and payload.daily_quota < 0) or (payload.monthly_quota is not None and payload.monthly_quota < 0):
        raise HTTPException(status_code=400, detail="Quota cannot be negative")
        
    before_state = await get_user_status(user_id, session)
    
    override = await session.get(UserQuotaOverride, user_id)
    if not override:
        override = UserQuotaOverride(user_id=user_id)
        session.add(override)
        
    if payload.daily_quota is not None: override.daily_quota_override = payload.daily_quota
    if payload.monthly_quota is not None: override.monthly_quota_override = payload.monthly_quota
    if payload.reason: override.reason = payload.reason
    override.updated_by_role = get_admin_role(admin_token).value
    
    await session.flush()
    after_state = await get_user_status(user_id, session)
    
    await audit_action(session, "quota_set", request, admin_token, str(user_id), payload.model_dump(), {"before": before_state["quota"], "after": after_state["quota"]}, "success")
    await session.commit()
    return after_state

@router.delete("/users/{user_id}/quota/override", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def delete_user_quota_override(user_id: uuid.UUID, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    override = await session.get(UserQuotaOverride, user_id)
    if override:
        await session.delete(override)
        await audit_action(session, "quota_override_delete", request, admin_token, str(user_id), None, {"status": "success"}, "success")
        await session.commit()
    return await get_user_status(user_id, session)

@router.get("/tokens/lookup", dependencies=[Depends(require_admin_role(AdminRole.READ)), Depends(admin_rate_limit)])
async def lookup_token(token: str, session: AsyncSession = Depends(get_db_session)):
    """Busca o proprietário de um token de API."""
    prefix = token[:12]
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.revoked_at.is_(None))
    )
    api_keys = result.scalars().all()
    api_key = next((item for item in api_keys if verify_secret(token, item.key_hash)), None)
    
    if not api_key:
        raise HTTPException(status_code=404, detail="Token não encontrado ou revogado")
        
    return await get_user_status(api_key.client_id, session)

@router.get("/plans", dependencies=[Depends(require_admin_role(AdminRole.READ)), Depends(admin_rate_limit)])
async def list_billing_plans(session: AsyncSession = Depends(get_db_session)):
    """Lista todos os planos de faturamento disponíveis."""
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.name))
    plans = result.scalars().all()
    return [{"id": str(p.id), "name": p.name, "code": p.code} for p in plans]

class PlanUpdateRequest(BaseModel):
    plan_id: uuid.UUID

@router.post("/users/{user_id}/plan", dependencies=[Depends(require_admin_role(AdminRole.WRITE)), Depends(admin_rate_limit)])
async def update_user_plan(user_id: uuid.UUID, payload: PlanUpdateRequest, request: Request, admin_token: str = Depends(admin_key_scheme), session: AsyncSession = Depends(get_db_session)):
    """Altera o plano de faturamento de um cliente."""
    client = await session.get(Client, user_id)
    if not client:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    plan = await session.get(BillingPlan, payload.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
        
    before_plan = str(client.billing_plan_id)
    client.billing_plan_id = plan.id
    client.updated_at = utc_now()
    
    await audit_action(session, "user_plan_update", request, admin_token, str(user_id), {"before_plan_id": before_plan, "after_plan_id": str(plan.id)}, {"status": "success"}, "success")
    await session.commit()
    
    return await get_user_status(user_id, session)

@router.get("/system/resources", dependencies=[Depends(require_admin_role(AdminRole.READ)), Depends(admin_rate_limit)])
async def get_system_resources():
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage('/')
    
    try:
        load_avg = os.getloadavg()
    except AttributeError:
        load_avg = (0.0, 0.0, 0.0)

    process = psutil.Process(os.getpid())
    
    gpu_info = {"available": False, "reason": "nvidia-smi check pending"}
    
    def parse_smi_output(output):
        lines = output.strip().split('\n')
        if lines and lines[0]:
            parts = [p.strip() for p in lines[0].split(',')]
            if len(parts) >= 7:
                def parse_int(idx):
                    val = parts[idx]
                    if val in ['[Not Supported]', '[Function Not Found]'] or not val.strip().replace('-','').isdigit():
                        return 0
                    return int(val)
                return {
                    "available": True,
                    "name": parts[0],
                    "vram_total_mb": parse_int(1),
                    "vram_used_mb": parse_int(2),
                    "vram_free_mb": parse_int(3),
                    "utilization_percent": parse_int(4),
                    "temperature_c": parse_int(5),
                    "power_draw_w": parts[6]
                }
        return None

    # Tenta local primeiro (com timeout curto)
    local_success = False
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=0.5
        )
        if res.returncode == 0:
            parsed = parse_smi_output(res.stdout)
            if parsed:
                gpu_info = parsed
                local_success = True
    except:
        pass

    # Se local falhou ou não disponível, tenta via Docker exec no container do data-plane
    if not local_success:
        try:
            import docker
            client = docker.from_env()
            # Procura o container do data-plane (gemma é o padrão)
            containers = client.containers.list(filters={"name": "data-plane-gemma"})
            if containers:
                target = containers[0]
                exec_res = target.exec_run("nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits")
                if exec_res.exit_code == 0:
                    parsed = parse_smi_output(exec_res.output.decode('utf-8'))
                    if parsed: gpu_info = parsed
                else:
                    gpu_info["reason"] = f"Remote nvidia-smi failed (code {exec_res.exit_code})"
            else:
                gpu_info["reason"] = "data-plane-gemma container not found"
        except ImportError:
            gpu_info["reason"] = "docker-py not installed"
        except Exception as e:
            gpu_info["reason"] = f"Docker fallback error: {str(e)}"

    return {
        "cpu_percent": psutil.cpu_percent(interval=1.0),
        "memory": {
            "total_mb": mem.total // (1024*1024),
            "used_mb": mem.used // (1024*1024),
            "free_mb": mem.available // (1024*1024),
            "percent": round(mem.used / mem.total * 100, 2) if mem.total > 0 else 0
        },
        "disk": {
            "total_gb": disk.total // (1024*1024*1024),
            "used_gb": disk.used // (1024*1024*1024),
            "free_gb": disk.free // (1024*1024*1024),
            "percent": round(disk.used / disk.total * 100, 2) if disk.total > 0 else 0
        },
        "uptime_seconds": time.time() - psutil.boot_time(),
        "load_average": load_avg,
        "process": {
            "pid": process.pid,
            "memory_mb": process.memory_info().rss // (1024*1024),
            "cpu_percent": process.cpu_percent(interval=0.1)
        },
        "gpu": gpu_info
    }

@router.get("/openrouter/models", dependencies=[Depends(require_admin_role(AdminRole.READ))])
async def list_openrouter_models():
    """Fetch available models from OpenRouter."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://openrouter.ai/api/v1/models", timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch OpenRouter models: {str(e)}")

@router.get("/openrouter/backend", dependencies=[Depends(require_admin_role(AdminRole.READ))])
async def get_openrouter_backend(session: AsyncSession = Depends(get_db_session)):
    """Check if OpenRouter backend is configured."""
    result = await session.execute(
        select(InferenceBackend).where(
            InferenceBackend.provider == "openrouter",
            InferenceBackend.is_active.is_(True)
        )
    )
    backend = result.scalars().first()
    if not backend:
        return {"configured": False}
    return {
        "configured": True,
        "id": str(backend.id),
        "name": backend.name,
        "base_url": backend.base_url
    }

class OpenRouterConfigureRequest(BaseModel):
    model_id: str
    model_alias: str


class OpenRouterApiRequest(BaseModel):
    api_key: str | None = None
    base_url: str | None = None


class OpenRouterDirectChatRequest(OpenRouterApiRequest):
    model_id: str
    prompt: str
    temperature: float = 0.2


def _openrouter_request_config(payload: OpenRouterApiRequest | None = None) -> tuple[str, str]:
    settings = get_settings()
    base_url = (payload.base_url if payload and payload.base_url else settings.openrouter_base_url) or "https://openrouter.ai/api/v1"
    api_key = (payload.api_key if payload and payload.api_key else settings.openrouter_api_key) or ""
    return base_url.rstrip("/"), api_key


@router.post("/openrouter/connection", dependencies=[Depends(require_admin_role(AdminRole.READ))])
async def test_openrouter_connection(payload: OpenRouterApiRequest):
    """Validate OpenRouter API connectivity using configured or provided credentials."""
    base_url, api_key = _openrouter_request_config(payload)
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:18080/static/openrouter-test/index.html",
        "X-Title": "LLM Inference Stack OpenRouter Test Lab",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"OpenRouter API error: {detail}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to connect to OpenRouter: {str(exc)}")

    return {
        "ok": True,
        "base_url": base_url,
        "using_configured_key": not bool(payload.api_key),
        "model_count": len(data.get("data", [])),
    }


@router.post("/openrouter/models", dependencies=[Depends(require_admin_role(AdminRole.READ))])
async def list_openrouter_models_authenticated(payload: OpenRouterApiRequest):
    """Fetch available models from OpenRouter using configured or provided credentials."""
    base_url, api_key = _openrouter_request_config(payload)
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:18080/static/openrouter-test/index.html",
        "X-Title": "LLM Inference Stack OpenRouter Test Lab",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"Failed to fetch OpenRouter models: {detail}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch OpenRouter models: {str(exc)}")


@router.post("/openrouter/chat", dependencies=[Depends(require_admin_role(AdminRole.READ))])
async def test_openrouter_chat(payload: OpenRouterDirectChatRequest):
    """Send a direct chat completion request to OpenRouter."""
    base_url, api_key = _openrouter_request_config(payload)
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:18080/static/openrouter-test/index.html",
        "X-Title": "LLM Inference Stack OpenRouter Test Lab",
    }
    body = {
        "model": payload.model_id,
        "messages": [{"role": "user", "content": payload.prompt}],
        "temperature": payload.temperature,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"OpenRouter chat failed: {detail}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"OpenRouter chat failed: {str(exc)}")

@router.post("/openrouter/configure", dependencies=[Depends(require_admin_role(AdminRole.WRITE))])
async def configure_openrouter_model(
    payload: OpenRouterConfigureRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Register/Update an OpenRouter model mapping."""
    # 1. Ensure backend exists
    result = await session.execute(
        select(InferenceBackend).where(
            InferenceBackend.provider == "openrouter",
            InferenceBackend.is_active.is_(True)
        )
    )
    backend = result.scalars().first()
    if not backend:
        raise HTTPException(status_code=400, detail="OpenRouter backend not found or inactive. Please configure it in Provider Settings first.")

    # 2. Check if model already exists in registry
    res_model = await session.execute(
        select(ModelRegistry).where(ModelRegistry.model_alias == payload.model_alias)
    )
    model = res_model.scalars().first()
    
    metadata = json.dumps({
        "backend": "openrouter",
        "backend_name": backend.name,
    })
    
    if not model:
        model = ModelRegistry(
            model_id=payload.model_id,
            model_alias=payload.model_alias,
            inference_backend_id=backend.id,
            provider="openrouter",
            model_file="",
            context_length=131072,
            is_active=True,
            is_default=False,
            status="configured",
            prompt_template="qwen", # default
            metadata_json=metadata,
        )
        session.add(model)
        await session.flush()
    else:
        model.model_id = payload.model_id
        model.inference_backend_id = backend.id
        model.provider = "openrouter"
        model.metadata_json = metadata
        model.is_active = True
        model.status = "configured"

    # 3. Ensure route exists
    res_route = await session.execute(
        select(ModelBackendRoute).where(
            ModelBackendRoute.model_registry_id == model.id,
            ModelBackendRoute.inference_backend_id == backend.id,
        )
    )
    route = res_route.scalars().first()
    if not route:
        route = ModelBackendRoute(
            model_registry_id=model.id,
            inference_backend_id=backend.id,
            priority=1,
            weight=100,
            state="healthy",
        )
        session.add(route)
    else:
        route.priority = 1
        route.weight = 100
        route.state = "healthy"
        
    await session.commit()
    return {"status": "success", "model_alias": payload.model_alias, "model_id": payload.model_id}
