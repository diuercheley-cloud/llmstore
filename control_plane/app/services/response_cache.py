from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

from app.core.config import get_settings
from app.core.metrics import record_cache_result
from app.core.time import utc_now
from app.models.request_log import RequestLog
from app.models.response_cache import ResponseCache
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
CACHE_SCHEMA_VERSION = 2


@dataclass
class CacheLookupResult:
    hit: bool
    payload: dict | None = None
    completion_tokens: int = 0
    prompt_tokens: int = 0


def _hash_json(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_chat_cache_key(
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    top_p: float,
    max_tokens: int,
    include_reasoning: bool,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
    parallel_tool_calls: bool | None = None,
    response_format: dict | None = None,
) -> tuple[str, str]:
    request_payload = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "kind": "chat",
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "include_reasoning": include_reasoning,
        "tools": tools,
        "tool_choice": tool_choice,
        "parallel_tool_calls": parallel_tool_calls,
        "response_format": response_format,
    }
    return _hash_json(request_payload), f"chat:{model}:{len(messages)}"


def build_completion_cache_key(
    *,
    model: str,
    prompt: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> tuple[str, str]:
    request_payload = {
        "kind": "completion",
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    return _hash_json(request_payload), f"completion:{model}:{len(prompt)}"


async def lookup_exact_cache(
    session: AsyncSession,
    *,
    endpoint: str,
    model: str,
    request_hash: str,
    plan_code: str | None = None,
) -> CacheLookupResult:
    if not settings.response_cache_enabled:
        record_cache_result(hit=False, model=model, backend="cache", plan=plan_code, endpoint=endpoint)
        return CacheLookupResult(hit=False)

    now = utc_now()
    stmt = select(ResponseCache).where(
        ResponseCache.cache_type == "exact",
        ResponseCache.endpoint_type == endpoint,
        ResponseCache.model == model,
        ResponseCache.request_hash == request_hash,
        ResponseCache.is_active.is_(True),
        ResponseCache.expires_at > now,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        record_cache_result(hit=False, model=model, backend="cache", plan=plan_code, endpoint=endpoint)
        return CacheLookupResult(hit=False)

    row.hit_count += 1
    row.last_hit_at = now
    row.updated_at = now
    record_cache_result(hit=True, model=model, backend="cache", plan=plan_code, endpoint=endpoint)
    return CacheLookupResult(
        hit=True,
        payload=json.loads(row.response_json),
        prompt_tokens=row.prompt_tokens_estimated,
        completion_tokens=row.completion_tokens_estimated,
    )


async def store_exact_cache(
    session: AsyncSession,
    *,
    endpoint: str,
    model: str,
    request_hash: str,
    request_fingerprint: str,
    response_payload: dict,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    if not settings.response_cache_enabled:
        return

    now = utc_now()
    expires_at = now + timedelta(seconds=settings.response_cache_ttl_seconds)
    row = (
        await session.execute(
            select(ResponseCache).where(
                ResponseCache.cache_type == "exact",
                ResponseCache.endpoint_type == endpoint,
                ResponseCache.model == model,
                ResponseCache.request_hash == request_hash,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = ResponseCache(
            cache_type="exact",
            endpoint_type=endpoint,
            model=model,
            request_hash=request_hash,
            request_fingerprint=request_fingerprint,
            response_json=json.dumps(response_payload, ensure_ascii=True),
            prompt_tokens_estimated=prompt_tokens,
            completion_tokens_estimated=completion_tokens,
            expires_at=expires_at,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return

    row.request_fingerprint = request_fingerprint
    row.response_json = json.dumps(response_payload, ensure_ascii=True)
    row.prompt_tokens_estimated = prompt_tokens
    row.completion_tokens_estimated = completion_tokens
    row.expires_at = expires_at
    row.is_active = True
    row.updated_at = now


async def clear_response_cache(session: AsyncSession) -> int:
    result = await session.execute(delete(ResponseCache))
    return int(result.rowcount or 0)


async def get_response_cache_stats(session: AsyncSession) -> dict:
    now = utc_now()
    cache_rows = (
        await session.execute(
            select(
                func.count(ResponseCache.id).label("entries_total"),
                func.count().filter(ResponseCache.expires_at <= now).label("expired_entries"),
                func.coalesce(func.sum(ResponseCache.hit_count), 0).label("cache_reuses"),
            )
        )
    ).mappings().first()
    request_rows = (
        await session.execute(
            select(
                func.count(RequestLog.id).label("requests_total"),
                func.count().filter(RequestLog.cache_hit.is_(True)).label("cache_hits_total"),
            )
        )
    ).mappings().first()
    requests_total = int(request_rows["requests_total"] or 0)
    cache_hits_total = int(request_rows["cache_hits_total"] or 0)
    return {
        "enabled": settings.response_cache_enabled,
        "semantic_cache_enabled": settings.semantic_cache_enabled,
        "ttl_seconds": settings.response_cache_ttl_seconds,
        "entries_total": int(cache_rows["entries_total"] or 0),
        "expired_entries": int(cache_rows["expired_entries"] or 0),
        "cache_reuses": int(cache_rows["cache_reuses"] or 0),
        "requests_total": requests_total,
        "cache_hits_total": cache_hits_total,
        "cache_misses_total": max(requests_total - cache_hits_total, 0),
        "cache_hit_rate": round((cache_hits_total / requests_total), 4) if requests_total else 0.0,
    }
