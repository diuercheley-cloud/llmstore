import uuid
from datetime import date, datetime, timezone
from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.billing_plan import BillingPlan
from app.models.quota_counter import QuotaCounter
from app.models.tts_usage_event import TtsUsageEvent
from app.services.billing import resolve_effective_plan
from app.services.quota import month_start


def _result_scalar(result, default=0):
    if hasattr(result, "scalar"):
        value = result.scalar()
    else:
        value = result.scalar_one_or_none()
    return default if value is None else value

async def get_tts_usage_and_limits(session: AsyncSession, client: Client) -> Dict[str, Any]:
    plan = resolve_effective_plan(client)
    
    today = date.today()
    this_month = month_start(today)
    
    # Get daily usage
    daily_result = await session.execute(
        select(QuotaCounter).where(
            QuotaCounter.client_id == client.id,
            QuotaCounter.period_start == today,
            QuotaCounter.period_type == "daily"
        )
    )
    daily_counter = daily_result.scalar_one_or_none()
    daily_usage = daily_counter.used_tts_chars if daily_counter else 0
    
    # Get monthly usage
    monthly_result = await session.execute(
        select(QuotaCounter).where(
            QuotaCounter.client_id == client.id,
            QuotaCounter.period_start == this_month,
            QuotaCounter.period_type == "monthly"
        )
    )
    monthly_counter = monthly_result.scalar_one_or_none()
    monthly_usage = monthly_counter.used_tts_chars if monthly_counter else 0
    
    return {
        "plan": plan.code,
        "limits": {
            "tts_enabled": plan.tts_enabled,
            "max_chars_per_request": plan.tts_chars_per_request,
            "max_chars_per_day": plan.tts_chars_per_day,
            "max_chars_per_month": plan.tts_chars_per_month,
            "max_files": plan.tts_max_files,
            "retention_days": plan.tts_audio_retention_days,
        },
        "usage": {
            "daily_chars": daily_usage,
            "monthly_chars": monthly_usage,
        }
    }

async def check_tts_feature_blocked(session: AsyncSession, client_id: uuid.UUID) -> tuple[bool, str | None]:
    # Placeholder for explicit feature blocking logic if needed
    # For now, we rely on plan.tts_enabled
    return False, None

async def record_tts_event(
    session: AsyncSession, 
    client_id: uuid.UUID, 
    chars: int, 
    api_key_prefix: str | None = None,
    audio_file_id: str | None = None,
    audio_size_bytes: int | None = None,
    plan_code: str | None = None,
    metadata: dict | None = None
):
    # Record detailed event
    event = TtsUsageEvent(
        client_id=client_id,
        api_key_prefix=api_key_prefix,
        chars_input=chars,
        audio_file_id=audio_file_id,
        audio_size_bytes=audio_size_bytes,
        plan_code=plan_code,
        metadata_json=metadata
    )
    session.add(event)
    
    # Update quota counters
    today = date.today()
    this_month = month_start(today)
    
    for period_start, period_type in [(today, "daily"), (this_month, "monthly")]:
        result = await session.execute(
            select(QuotaCounter).where(
                QuotaCounter.client_id == client_id,
                QuotaCounter.period_start == period_start,
                QuotaCounter.period_type == period_type
            )
        )
        counter = result.scalar_one_or_none()
        if not counter:
            counter = QuotaCounter(
                client_id=client_id,
                period_start=period_start,
                period_type=period_type,
                used_tts_chars=0
            )
            session.add(counter)
            await session.flush()
        
        counter.used_tts_chars += chars

async def ensure_tts_quota(session: AsyncSession, client: Client, requested_chars: int):
    usage_info = await get_tts_usage_and_limits(session, client)
    limits = usage_info["limits"]
    usage = usage_info["usage"]
    
    if not limits["tts_enabled"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="TTS feature not enabled for your plan")
        
    if requested_chars > limits["max_chars_per_request"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail=f"Request exceeds maximum characters per request ({limits['max_chars_per_request']})")
        
    if usage["daily_chars"] + requested_chars > limits["max_chars_per_day"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="Daily TTS character quota exceeded")
        
    if usage["monthly_chars"] + requested_chars > limits["max_chars_per_month"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="Monthly TTS character quota exceeded")

async def get_admin_tts_usage(session: AsyncSession):
    # Get total TTS usage for all clients
    # Today
    today = date.today()
    this_month = month_start(today)
    
    daily_query = select(func.sum(QuotaCounter.used_tts_chars)).where(
        QuotaCounter.period_start == today,
        QuotaCounter.period_type == "daily"
    )
    daily_total = _result_scalar(await session.execute(daily_query), 0)
    
    monthly_query = select(func.sum(QuotaCounter.used_tts_chars)).where(
        QuotaCounter.period_start == this_month,
        QuotaCounter.period_type == "monthly"
    )
    monthly_total = _result_scalar(await session.execute(monthly_query), 0)
    
    # Usage by client
    client_usage_query = select(
        Client.id,
        Client.name,
        QuotaCounter.used_tts_chars,
        QuotaCounter.period_type
    ).join(QuotaCounter, Client.id == QuotaCounter.client_id).where(
        QuotaCounter.period_start == this_month,
        QuotaCounter.period_type == "monthly"
    )
    client_usage_exec = await session.execute(client_usage_query)
    if hasattr(client_usage_exec, "all"):
        client_usage_results = client_usage_exec.all()
    else:
        client_usage_results = []
    
    usage_by_client = [
        {
            "client_id": str(r.id),
            "client_name": r.name,
            "monthly_chars": r.used_tts_chars
        }
        for r in client_usage_results
    ]
    
    # Total files and storage (approx from events)
    stats_query = select(
        func.count(TtsUsageEvent.id),
        func.sum(TtsUsageEvent.audio_size_bytes)
    ).where(TtsUsageEvent.created_at >= datetime.combine(this_month, datetime.min.time(), tzinfo=timezone.utc))
    stats_exec = await session.execute(stats_query)
    if hasattr(stats_exec, "one"):
        stats_result = stats_exec.one()
    else:
        count_value = _result_scalar(stats_exec, 0)
        stats_result = (count_value, 0)
    
    return {
        "total_chars_today": daily_total,
        "total_chars_month": monthly_total,
        "total_files_month": stats_result[0] or 0,
        "total_storage_bytes_month": stats_result[1] or 0,
        "usage_by_client": usage_by_client
    }
