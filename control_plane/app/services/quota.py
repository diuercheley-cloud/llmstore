from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota_counter import QuotaCounter
from app.models.usage_record import UsageRecord


class QuotaExceeded(Exception):
    pass


def month_start(today: date) -> date:
    return date(today.year, today.month, 1)


async def ensure_quota(session: AsyncSession, client_id, daily_limit: int, monthly_limit: int, incoming_tokens: int) -> None:
    today = date.today()
    daily = await _get_or_create_counter(session, client_id, today, "daily")
    monthly = await _get_or_create_counter(session, client_id, month_start(today), "monthly")
    if daily.used_tokens + incoming_tokens > daily_limit:
        raise QuotaExceeded("daily token quota exceeded")
    if monthly.used_tokens + incoming_tokens > monthly_limit:
        raise QuotaExceeded("monthly token quota exceeded")


async def record_usage(session: AsyncSession, client_id, prompt_tokens: int, completion_tokens: int) -> None:
    total = prompt_tokens + completion_tokens
    today = date.today()
    for period_start, period_type in ((today, "daily"), (month_start(today), "monthly")):
        counter = await _get_or_create_counter(session, client_id, period_start, period_type)
        counter.used_tokens += total
        counter.used_requests += 1
        usage_record = await _get_or_create_usage_record(session, client_id, period_start, period_type)
        usage_record.request_count += 1
        usage_record.prompt_tokens += prompt_tokens
        usage_record.completion_tokens += completion_tokens


async def _get_or_create_counter(session: AsyncSession, client_id, period_start: date, period_type: str) -> QuotaCounter:
    result = await session.execute(
        select(QuotaCounter).where(
            QuotaCounter.client_id == client_id,
            QuotaCounter.period_start == period_start,
            QuotaCounter.period_type == period_type,
        )
    )
    counter = result.scalar_one_or_none()
    if counter:
        return counter
    counter = QuotaCounter(client_id=client_id, period_start=period_start, period_type=period_type)
    session.add(counter)
    await session.flush()
    return counter


async def _get_or_create_usage_record(session: AsyncSession, client_id, period_start: date, period_type: str) -> UsageRecord:
    result = await session.execute(
        select(UsageRecord).where(
            UsageRecord.client_id == client_id,
            UsageRecord.period_start == period_start,
            UsageRecord.period_type == period_type,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        return record
    record = UsageRecord(client_id=client_id, period_start=period_start, period_type=period_type)
    session.add(record)
    await session.flush()
    return record
