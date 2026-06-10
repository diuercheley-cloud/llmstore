import os
import subprocess
import time
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.core.client import Client
from app.models.core.quota_counter import QuotaCounter
from app.models.core.usage_record import UsageRecord
from app.schemas.admin import TestCommand, TestRunRequest, TestRunResponse
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin-tests"], dependencies=[Depends(require_admin)])

WHITELISTED_COMMANDS = {
    "health-full": {"name": "Health full", "description": "Run full system health validation", "command": "./scripts/validate-system-health.sh --full"},
    "local-smoke": {"name": "Local production smoke", "description": "Run local production smoke tests", "command": "./scripts/local-production-smoke.sh"},
    "ui-health": {"name": "UI health", "description": "Check UI health", "command": "./scripts/ui-health.sh"},
    "validate-e2e": {"name": "Validate E2E", "description": "Run full E2E validation", "command": "./scripts/validate-e2e.sh"},
    "backup": {"name": "Backup", "description": "Trigger system backup", "command": "./scripts/backup.sh"},
    "dr-test": {"name": "DR test", "description": "Run Disaster Recovery test", "command": "./scripts/dr-test.sh"},
    "benchmark": {"name": "Benchmark quick", "description": "Run quick benchmark", "command": "./scripts/benchmark.sh --quick"},
    "test-fallback": {"name": "Real fallback test", "description": "Test real-world fallback routing", "command": "./scripts/test-real-fallback.sh"},
}


@router.post("/test/clients/{client_id}/reset-usage")
async def reset_client_usage(client_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    current_settings = get_settings()
    if not current_settings.test_tools_enabled or current_settings.public_exposure:
        raise HTTPException(status_code=403, detail="test tools disabled")
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    await session.execute(
        select(QuotaCounter).where(QuotaCounter.client_id == client_id)
    )
    # Delete all quota counters for this client to reset usage
    from sqlalchemy import delete
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
        # Run command with 60s timeout
        # Using shell=True because we trust WHITELISTED_COMMANDS and it's local test only
        env = os.environ.copy()
        env["BASE_URL"] = "http://localhost:8080"

        result = subprocess.run(
            cmd_info["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parents[2]), # project root (/app)
            env=env
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
            created_at=utc_now()
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
            created_at=utc_now()
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
            created_at=utc_now()
        )
