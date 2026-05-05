import uuid
import psutil
import subprocess
import shutil
import os
import time
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update, desc
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
from app.core.time import utc_now
from app.core.config import get_settings
from app.core.security import verify_secret
from pydantic import BaseModel

router = APIRouter(prefix="/admin/tests", tags=["admin_tests"])

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
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.0
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                parts = [p.strip() for p in lines[0].split(',')]
                if len(parts) >= 7:
                    gpu_info = {
                        "available": True,
                        "name": parts[0],
                        "vram_total_mb": int(parts[1]) if parts[1] != '[Not Supported]' else 0,
                        "vram_used_mb": int(parts[2]) if parts[2] != '[Not Supported]' else 0,
                        "vram_free_mb": int(parts[3]) if parts[3] != '[Not Supported]' else 0,
                        "utilization_percent": int(parts[4]) if parts[4] != '[Not Supported]' else 0,
                        "temperature_c": int(parts[5]) if parts[5] != '[Not Supported]' else 0,
                        "power_draw_w": parts[6]
                    }
        else:
            gpu_info["reason"] = "nvidia-smi returned non-zero code"
    except FileNotFoundError:
        gpu_info["reason"] = "nvidia-smi not found"
    except subprocess.TimeoutExpired:
        gpu_info["reason"] = "nvidia-smi timeout"
    except Exception as e:
        gpu_info["reason"] = f"Unexpected error: {str(e)}"

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
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
