from datetime import date, timedelta

from app.models.quota_counter import QuotaCounter
from app.models.usage_record import UsageRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class QuotaExceeded(Exception):
    pass


def month_start(today: date) -> date:
    return date(today.year, today.month, 1)


def week_start(today: date) -> date:
    # Returns the Monday of the current week
    return today - timedelta(days=today.weekday())


async def ensure_quota(session: AsyncSession, client_id, daily_limit: int, weekly_limit: int, monthly_limit: int, incoming_tokens: int, requests_per_day_limit: int = 0) -> None:
    today = date.today()
    daily = await _get_or_create_counter(session, client_id, today, "daily")
    weekly = await _get_or_create_counter(session, client_id, week_start(today), "weekly")
    monthly = await _get_or_create_counter(session, client_id, month_start(today), "monthly")
    
    if requests_per_day_limit > 0 and daily.used_requests + 1 > requests_per_day_limit:
        raise QuotaExceeded("daily request quota exceeded")
        
    if daily.used_tokens + incoming_tokens > daily_limit:
        raise QuotaExceeded("daily token quota exceeded")
    if weekly.used_tokens + incoming_tokens > weekly_limit:
        raise QuotaExceeded("weekly token quota exceeded")
    if monthly.used_tokens + incoming_tokens > monthly_limit:
        raise QuotaExceeded("monthly token quota exceeded")


async def ensure_embeddings_quota(session: AsyncSession, client_id, monthly_requests_limit: int, monthly_tokens_limit: int, incoming_tokens: int) -> None:
    today = date.today()
    monthly = await _get_or_create_counter(session, client_id, month_start(today), "monthly")
    
    if monthly_requests_limit > 0 and monthly.used_embeddings_requests + 1 > monthly_requests_limit:
        raise QuotaExceeded("monthly embeddings requests quota exceeded")
    if monthly_tokens_limit > 0 and monthly.used_embeddings_tokens + incoming_tokens > monthly_tokens_limit:
        raise QuotaExceeded("monthly embeddings tokens quota exceeded")


async def record_usage(
    session: AsyncSession, 
    client_id, 
    prompt_tokens: int, 
    completion_tokens: int,
    token_count_method: str | None = None,
    tokens_estimated: bool = True
) -> None:
    total = prompt_tokens + completion_tokens
    today = date.today()
    for period_start, period_type in ((today, "daily"), (week_start(today), "weekly"), (month_start(today), "monthly")):
        counter = await _get_or_create_counter(session, client_id, period_start, period_type)
        counter.used_tokens += total
        counter.used_requests += 1
        usage_record = await _get_or_create_usage_record(session, client_id, period_start, period_type)
        usage_record.request_count += 1
        usage_record.prompt_tokens += prompt_tokens
        usage_record.completion_tokens += completion_tokens
        usage_record.token_count_method = token_count_method
        usage_record.tokens_estimated = tokens_estimated


async def record_embedding_usage(
    session: AsyncSession, 
    client_id, 
    input_count: int, 
    tokens: int,
    token_count_method: str | None = None,
    tokens_estimated: bool = True
) -> None:
    today = date.today()
    for period_start, period_type in ((today, "daily"), (week_start(today), "weekly"), (month_start(today), "monthly")):
        counter = await _get_or_create_counter(session, client_id, period_start, period_type)
        counter.used_embeddings_requests += 1
        counter.used_embeddings_tokens += tokens
        usage_record = await _get_or_create_usage_record(session, client_id, period_start, period_type)
        usage_record.embeddings_requests += 1
        usage_record.embeddings_tokens += tokens
        usage_record.token_count_method = token_count_method
        usage_record.tokens_estimated = tokens_estimated


async def update_usage_with_real_tokens(
    session: AsyncSession,
    client_id,
    estimated_prompt: int,
    estimated_completion: int,
    real_prompt: int,
    real_completion: int,
    token_count_method: str | None = None,
) -> None:
    prompt_diff = real_prompt - estimated_prompt
    completion_diff = real_completion - estimated_completion
    total_diff = prompt_diff + completion_diff

    today = date.today()
    for period_start, period_type in ((today, "daily"), (week_start(today), "weekly"), (month_start(today), "monthly")):
        counter = await _get_or_create_counter(session, client_id, period_start, period_type)
        counter.used_tokens += total_diff

        usage_record = await _get_or_create_usage_record(session, client_id, period_start, period_type)
        usage_record.prompt_tokens += prompt_diff
        usage_record.completion_tokens += completion_diff
        usage_record.token_count_method = token_count_method
        usage_record.tokens_estimated = False



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
