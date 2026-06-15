import asyncio
import os
import shlex
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import psutil
from app.core.config import get_settings
from app.core.security import verify_secret
from app.core.time import utc_now
from app.models.billing.billing_plan import BillingPlan
from app.models.core.admin_action_log import AdminActionLog
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.models.core.client_feature_block import ClientFeatureBlock
from app.models.core.quota_counter import QuotaCounter
from app.models.core.usage_record import UsageRecord
from app.schemas.admin import TestCommand, TestRunRequest, TestRunResponse
from app.services.auth import get_admin_role, require_admin
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# In-memory pytest run state
# ---------------------------------------------------------------------------

_pytest_runs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)

TESTS_DIR = Path(__file__).resolve().parents[3] / "tests"

CATEGORY_MAP: dict[str, str] = {
    "control_plane": "agent",
    "api": "api",
    "security": "security",
    "billing": "billing",
    "providers": "providers",
    "commercial": "commercial",
    "operations": "operations",
    "rag": "rag",
    "models": "models",
    "governance": "governance",
    "architecture": "governance",
    "backup": "operations",
    "chaos": "operations",
    "cache": "operations",
    "smoke": "operations",
    "audit": "admin",
    "rate_limit": "api",
    "e2e": "commercial",
    "inference": "providers",
    "integration": "commercial",
    "contract": "api",
    "unit": "agent",
    "data": "operations",
    "snapshots": "operations",
    "fixtures": "operations",
    "test_builds": "releases",
}


def _discover_tests() -> list[dict]:
    files = sorted(TESTS_DIR.rglob("test_*.py"))
    result = []
    for f in files:
        rel = f.relative_to(TESTS_DIR)
        parts = rel.parts
        category = "default"
        if len(parts) > 1:
            category = CATEGORY_MAP.get(parts[0], parts[0])
        result.append({"filename": str(rel), "category": category})
    return result


router = APIRouter(prefix="/admin", tags=["admin-tests"], dependencies=[Depends(require_admin)])

WHITELISTED_COMMANDS = {
    "health-full": {
        "name": "Health full",
        "description": "Run full system health validation",
        "command": "./scripts/validate-system-health.sh --full",
    },
    "local-smoke": {
        "name": "Local production smoke",
        "description": "Run local production smoke tests",
        "command": "./scripts/local-production-smoke.sh",
    },
    "ui-health": {
        "name": "UI health",
        "description": "Check UI health",
        "command": "./scripts/ui-health.sh",
    },
    "validate-e2e": {
        "name": "Validate E2E",
        "description": "Run full E2E validation",
        "command": "./scripts/validate-e2e.sh",
    },
    "backup": {
        "name": "Backup",
        "description": "Trigger system backup",
        "command": "./scripts/backup.sh",
    },
    "dr-test": {
        "name": "DR test",
        "description": "Run Disaster Recovery test",
        "command": "./scripts/dr-test.sh",
    },
    "benchmark": {
        "name": "Benchmark quick",
        "description": "Run quick benchmark",
        "command": "./scripts/benchmark.sh --quick",
    },
    "test-fallback": {
        "name": "Real fallback test",
        "description": "Test real-world fallback routing",
        "command": "./scripts/test-real-fallback.sh",
    },
}


# ---------------------------------------------------------------------------
# Helper: build a user/quotas response matching the admin-tests HTML page
# ---------------------------------------------------------------------------


async def _client_quota_response(client: Client, session: AsyncSession) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    daily_result = await session.execute(
        select(func.coalesce(func.sum(QuotaCounter.used_tokens), 0)).where(
            QuotaCounter.client_id == client.id,
            QuotaCounter.period_start == today,
            QuotaCounter.period_type == "day",
        )
    )
    daily = daily_result.scalar() or 0

    monthly_result = await session.execute(
        select(func.coalesce(func.sum(QuotaCounter.used_tokens), 0)).where(
            QuotaCounter.client_id == client.id,
            QuotaCounter.period_start == month_start,
            QuotaCounter.period_type == "month",
        )
    )
    monthly = monthly_result.scalar() or 0

    daily_limit = client.daily_token_quota or 100_000_000
    monthly_limit = client.monthly_token_quota or 1_000_000_000

    return {
        "id": str(client.id),
        "name": client.name,
        "status": client.billing_status,
        "blocked": client.is_blocked,
        "quota": {
            "daily_used": int(daily),
            "monthly_used": int(monthly),
            "effectiveDailyLimit": daily_limit,
            "effectiveMonthlyLimit": monthly_limit,
            "daily_remaining": max(0, daily_limit - int(daily)),
            "monthly_remaining": max(0, monthly_limit - int(monthly)),
        },
    }


# ---------------------------------------------------------------------------
# OpenRouter helpers
# ---------------------------------------------------------------------------


async def _fetch_openrouter_model_metadata(model_id: str) -> dict:
    """Fetch model metadata from OpenRouter API."""
    import httpx
    settings = get_settings()
    api_key = settings.openrouter_api_key or ""
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://openrouter.ai/api/v1/models/{model_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.get("/tests/auth/whoami")
async def tests_whoami(request: Request):
    token = request.headers.get("X-Admin-Token", "")
    role = get_admin_role(token)
    if role is None:
        raise HTTPException(status_code=401, detail="invalid admin token")
    return {"authenticated": True, "role": role.value}


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------


@router.get("/tests/plans")
async def tests_list_plans(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))
    plans = result.scalars().all()
    return [{"id": str(p.id), "name": p.name, "code": p.code} for p in plans]


# ---------------------------------------------------------------------------
# System Resources
# ---------------------------------------------------------------------------


@router.get("/tests/system/resources")
async def tests_system_resources():
    def _get_gpu_metrics():
        try:
            output = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            gpus = []
            for line in output.strip().split("\n"):
                parts = [p.strip() for p in line.split(", ")]
                if len(parts) >= 6:
                    gpus.append(
                        {
                            "index": int(parts[0]),
                            "name": parts[1],
                            "utilization": float(parts[2]),
                            "memory_used": float(parts[3]),
                            "memory_total": float(parts[4]),
                            "temperature": float(parts[5]),
                        }
                    )
            return gpus
        except Exception:
            return []

    gpus = _get_gpu_metrics()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "cpu_count": psutil.cpu_count(),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
            "used": psutil.disk_usage("/").used,
            "free": psutil.disk_usage("/").free,
            "percent": psutil.disk_usage("/").percent,
        },
        "gpu": {
            "available": len(gpus) > 0,
            "count": len(gpus),
            "devices": gpus,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Token Lookup
# ---------------------------------------------------------------------------


@router.get("/tests/tokens/lookup")
async def tests_token_lookup(
    token: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
):
    prefix = token[:12]
    result = await session.execute(
        select(ApiKey)
        .where(
            ApiKey.key_prefix == prefix,
            ApiKey.is_active == True,
            ApiKey.revoked_at.is_(None),
        )
        .order_by(ApiKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    api_key = next((item for item in api_keys if verify_secret(token, item.key_hash)), None)
    if api_key is None:
        raise HTTPException(status_code=404, detail="token not found")
    client = await session.get(Client, api_key.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return await _client_quota_response(client, session)


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------


@router.get("/tests/users/{user_id}")
async def tests_get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return await _client_quota_response(client, session)


@router.post("/tests/users/{user_id}/block")
async def tests_block_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = True
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return await _client_quota_response(client, session)


@router.post("/tests/users/{user_id}/unblock")
async def tests_unblock_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = False
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return await _client_quota_response(client, session)


@router.post("/tests/users/{user_id}/plan")
async def tests_set_user_plan(
    user_id: uuid.UUID,
    body: dict,
    session: AsyncSession = Depends(get_db_session),
):
    plan_id = body.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id required")
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    plan = await session.get(BillingPlan, uuid.UUID(plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    client.billing_plan_id = plan.id
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return await _client_quota_response(client, session)


# ---------------------------------------------------------------------------
# Quota Management
# ---------------------------------------------------------------------------


@router.post("/tests/users/{user_id}/quota/reset")
async def tests_reset_quota(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await session.execute(delete(QuotaCounter).where(QuotaCounter.client_id == user_id))
    await session.execute(delete(UsageRecord).where(UsageRecord.client_id == user_id))
    await session.commit()
    return await _client_quota_response(client, session)


@router.post("/tests/users/{user_id}/quota/renew")
async def tests_renew_quota(user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await session.execute(
        delete(QuotaCounter).where(
            QuotaCounter.client_id == user_id,
            QuotaCounter.period_start < date.today(),
        )
    )
    await session.commit()
    return await _client_quota_response(client, session)


@router.post("/tests/users/{user_id}/quota/set")
async def tests_set_quota(
    user_id: uuid.UUID,
    body: dict,
    session: AsyncSession = Depends(get_db_session),
):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    daily = body.get("daily_quota")
    monthly = body.get("monthly_quota")
    if daily is not None:
        if int(daily) < 0:
            raise HTTPException(status_code=400, detail="daily_quota must be >= 0")
        client.daily_token_quota = int(daily)
    if monthly is not None:
        if int(monthly) < 0:
            raise HTTPException(status_code=400, detail="monthly_quota must be >= 0")
        client.monthly_token_quota = int(monthly)
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return await _client_quota_response(client, session)


@router.delete("/tests/users/{user_id}/quota/override")
async def tests_delete_quota_override(
    user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
):
    client = await session.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.daily_token_quota = 0
    client.monthly_token_quota = 0
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return await _client_quota_response(client, session)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@router.get("/tests/audit")
async def tests_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "admin_role": log.admin_role,
            "action": log.action,
            "target_user_id": log.target_user_id,
            "status": log.status,
            "request_path": log.request_path,
            "request_method": log.request_method,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# RAG Status & Per-Client RAG
# ---------------------------------------------------------------------------


@router.get("/tests/rag/status")
async def tests_rag_status(session: AsyncSession = Depends(get_db_session)):
    total_docs = await session.execute(select(func.count()).select_from(ClientFeatureBlock))
    total_blocks = total_docs.scalar() or 0

    rag_blocks = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.feature == "rag", ClientFeatureBlock.blocked.is_(True)
        )
    )
    blocked_clients = rag_blocks.scalars().all()

    return {
        "status": "operational",
        "blocked_clients_count": len(blocked_clients),
        "total_feature_blocks": total_blocks,
        "rag_enabled": True,
    }


@router.get("/tests/rag/clients/{client_id}/usage")
async def tests_rag_client_usage(
    client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    blocked, reason = False, None
    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag",
        )
    )
    block = block_result.scalar_one_or_none()
    if block and block.blocked:
        blocked = True
        reason = block.reason

    doc_count = await session.execute(
        select(func.count())
        .select_from(UsageRecord)
        .where(
            UsageRecord.client_id == client_id,
        )
    )

    return {
        "client_id": str(client_id),
        "client_name": client.name,
        "blocked": blocked,
        "block_reason": reason,
        "documents_count": doc_count.scalar() or 0,
    }


@router.post("/tests/rag/clients/{client_id}/block")
async def tests_rag_block(
    client_id: uuid.UUID,
    body: dict = {},
    session: AsyncSession = Depends(get_db_session),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag",
        )
    )
    block = result.scalar_one_or_none()
    if block is None:
        block = ClientFeatureBlock(
            client_id=client_id,
            feature="rag",
            blocked=True,
            reason=body.get("reason", "blocked by admin"),
        )
        session.add(block)
    else:
        block.blocked = True
        block.reason = body.get("reason", "blocked by admin")
        block.updated_at = utc_now()

    await session.commit()
    return {"status": "blocked", "client_id": str(client_id)}


@router.post("/tests/rag/clients/{client_id}/unblock")
async def tests_rag_unblock(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag",
        )
    )
    block = result.scalar_one_or_none()
    if block is not None:
        block.blocked = False
        block.reason = None
        block.updated_at = utc_now()
        await session.commit()

    return {"status": "unblocked", "client_id": str(client_id)}


# ---------------------------------------------------------------------------
# Pytest Runner
# ---------------------------------------------------------------------------


class PytestRunRequest(BaseModel):
    files: list[str]
    timeout: int = 120


@router.get("/tests/pytest/files")
async def tests_pytest_files():
    files = _discover_tests()
    return {"files": files}


@router.post("/tests/pytest/run")
async def tests_pytest_run(body: PytestRunRequest):
    run_id = str(uuid.uuid4())
    start_time = time.time()
    test_files = body.files
    timeout = body.timeout
    now = datetime.utcnow()

    run_state = {
        "run_id": run_id,
        "status": "running",
        "total": len(test_files),
        "completed": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "timeouts": 0,
        "elapsed_seconds": 0,
        "results": {},
        "start_time": start_time,
        "cancelled": False,
    }
    _pytest_runs[run_id] = run_state

    async def _run():
        loop = asyncio.get_event_loop()
        for filename in test_files:
            if run_state["cancelled"]:
                break
            filepath = TESTS_DIR / filename
            if not filepath.exists():
                run_state["results"][filename] = {
                    "status": "error",
                    "output": f"File not found: {filename}",
                    "duration": 0,
                }
                run_state["errors"] += 1
                run_state["completed"] += 1
                continue
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "pytest",
                    str(filepath),
                    "-v",
                    "--tb=short",
                    "--no-header",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(TESTS_DIR.parent),
                )
                try:
                    stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                except TimeoutError:
                    proc.kill()
                    await proc.wait()
                    run_state["results"][filename] = {
                        "status": "timeout",
                        "output": f"Test timed out after {timeout}s",
                        "duration": timeout,
                    }
                    run_state["timeouts"] += 1
                    run_state["completed"] += 1
                    continue
                output = stdout_bytes.decode("utf-8", errors="replace")
                elapsed = round(time.time() - start_time, 2)
                if proc.returncode == 0:
                    status = "passed"
                    run_state["passed"] += 1
                elif proc.returncode == 1:
                    status = "failed"
                    run_state["failed"] += 1
                else:
                    status = "error"
                    run_state["errors"] += 1
                run_state["results"][filename] = {
                    "status": status,
                    "output": output,
                    "duration": elapsed,
                }
            except Exception as e:
                run_state["results"][filename] = {
                    "status": "error",
                    "output": str(e),
                    "duration": 0,
                }
                run_state["errors"] += 1
            run_state["completed"] += 1
        run_state["elapsed_seconds"] = round(time.time() - start_time, 2)
        run_state["status"] = "cancelled" if run_state["cancelled"] else "completed"

    asyncio.ensure_future(_run())
    return {"run_id": run_id}


@router.get("/tests/pytest/run/{run_id}/status")
async def tests_pytest_status(run_id: str):
    run = _pytest_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    run["elapsed_seconds"] = round(time.time() - run["start_time"], 2)
    return run


@router.post("/tests/pytest/run/{run_id}/cancel")
async def tests_pytest_cancel(run_id: str):
    run = _pytest_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    run["cancelled"] = True
    return {"status": "cancelling", "run_id": run_id}


# ---------------------------------------------------------------------------
# Existing routes (preserved)
# ---------------------------------------------------------------------------


@router.post("/test/clients/{client_id}/reset-usage")
async def reset_client_usage(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    current_settings = get_settings()
    if not current_settings.test_tools_enabled or current_settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    await session.execute(select(QuotaCounter).where(QuotaCounter.client_id == client_id))
    await session.execute(delete(QuotaCounter).where(QuotaCounter.client_id == client_id))
    await session.execute(delete(UsageRecord).where(UsageRecord.client_id == client_id))
    await session.commit()
    return {"status": "reset", "client_id": str(client_id)}


@router.get("/test/commands", response_model=list[TestCommand])
async def list_test_commands():
    current_settings = get_settings()
    if not current_settings.test_tools_enabled or current_settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    return [
        TestCommand(id=k, name=v["name"], description=v["description"], command=v["command"])
        for k, v in WHITELISTED_COMMANDS.items()
    ]


@router.post("/test/run", response_model=TestRunResponse)
async def run_test_command(payload: TestRunRequest):
    current_settings = get_settings()
    if not current_settings.test_tools_enabled or current_settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")

    cmd_info = WHITELISTED_COMMANDS.get(payload.command_id)
    if not cmd_info:
        raise HTTPException(status_code=404, detail="command not found")

    start_time = time.time()
    run_id = str(uuid.uuid4())

    try:
        env = os.environ.copy()
        env["BASE_URL"] = "http://localhost:8080"

        result = subprocess.run(
            shlex.split(cmd_info["command"]),
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parents[2]),
            env=env,
        )
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="completed" if result.returncode == 0 else "failed",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            duration_seconds=round(duration, 2),
            created_at=utc_now(),
        )
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="timeout",
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "Timeout after 60s",
            exit_code=124,
            duration_seconds=round(duration, 2),
            created_at=utc_now(),
        )
    except Exception as e:
        duration = time.time() - start_time
        return TestRunResponse(
            run_id=run_id,
            command_id=payload.command_id,
            status="error",
            stderr=str(e),
            exit_code=1,
            duration_seconds=round(duration, 2),
            created_at=utc_now(),
        )
