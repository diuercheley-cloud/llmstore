from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import timedelta

from app.core.config import get_settings
from app.core.metrics import record_cache_result
from app.core.time import utc_now
from app.models.core.cache_policy import CachePolicy
from app.models.core.request_log import RequestLog
from app.models.core.response_cache import ResponseCache
from app.models.core.semantic_cache_entry import SemanticCacheEntry
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

CACHE_SCHEMA_VERSION = 3
DEFAULT_TTL_EXACT = 3600
CACHE_TTL_24H = 86400
CACHE_TTL_7D = 604800
DEFAULT_SEMANTIC_THRESHOLD = 0.85


@dataclass
class CacheLookupResult:
    hit: bool
    payload: dict | None = None
    completion_tokens: int = 0
    prompt_tokens: int = 0
    cache_type: str = "none"
    similarity_score: float = 0.0
    cached_entry_id: str | None = None


@dataclass
class CacheStats:
    exact_entries: int = 0
    semantic_entries: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    exact_misses: int = 0
    semantic_misses: int = 0
    total_requests: int = 0
    cache_hit_rate: float = 0.0
    expired_entries: int = 0
    enabled: bool = True
    semantic_enabled: bool = False
    ttl_seconds: int = 3600
    entries_total: int = 0
    cache_reuses: int = 0


def _hash_json(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _hash_str(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_request(
    *,
    messages: list[dict] | None = None,
    prompt: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 512,
    model: str = "",
    include_reasoning: bool = False,
) -> dict:
    payload: dict = {"cache_schema_version": CACHE_SCHEMA_VERSION}
    if messages is not None:
        normalized = []
        for msg in messages:
            normalized.append({"role": msg.get("role", ""), "content": msg.get("content", "")})
        payload["messages"] = normalized
    if prompt is not None:
        payload["prompt"] = prompt.strip()
    payload["temperature"] = round(temperature, 4)
    payload["top_p"] = round(top_p, 4)
    payload["max_tokens"] = max_tokens
    payload["model"] = model
    payload["include_reasoning"] = include_reasoning
    return payload


def build_cache_key(
    *,
    model: str,
    endpoint_type: str,
    messages: list[dict] | None = None,
    prompt: str | None = None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    include_reasoning: bool = False,
    client_id: str | None = None,
) -> tuple[str, str, str]:
    normalized = normalize_request(
        messages=messages,
        prompt=prompt,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        model=model,
        include_reasoning=include_reasoning,
    )
    request_hash = _hash_json(normalized)
    prefix = (
        f"chat:{model}:{len(messages)}" if messages else f"completion:{model}:{len(prompt or '')}"
    )
    fingerprint = hashlib.sha256(f"{prefix}:{request_hash}:{client_id or ''}".encode()).hexdigest()[
        :16
    ]
    return request_hash, prefix, fingerprint


def _deterministic_embedding(prompt_hash: str, dimensions: int = 384) -> list[float]:
    seed = int(prompt_hash[:16], 16)
    rng_state = seed
    embedding = []
    for _ in range(dimensions):
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        embedding.append((rng_state % 200000) / 100000.0 - 1.0)
    return embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def should_cache(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    endpoint_type: str = "",
    no_cache: bool = False,
    sensitive_prompt: bool = False,
    billing_plan_code: str | None = None,
) -> tuple[bool, bool, int]:
    if no_cache:
        return False, False, 0
    if not settings.response_cache_enabled:
        return False, False, 0
    cache_enabled = True
    semantic_enabled = settings.semantic_cache_enabled
    ttl = settings.response_cache_ttl_seconds
    if client_id:
        policy = await _get_cache_policy(
            session, client_id=client_id, billing_plan_code=billing_plan_code
        )
        if policy:
            cache_enabled = policy.cache_enabled
            semantic_enabled = policy.semantic_cache_enabled
            ttl = policy.cache_ttl_seconds
            if not policy.cache_sensitive_data_allowed and sensitive_prompt:
                cache_enabled = False
    return cache_enabled, semantic_enabled, ttl


async def _get_cache_policy(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    billing_plan_code: str | None = None,
) -> CachePolicy | None:
    if client_id:
        result = await session.execute(
            select(CachePolicy).where(CachePolicy.client_id == client_id)
        )
        policy = result.scalar_one_or_none()
        if policy:
            return policy
    if billing_plan_code:
        result = await session.execute(
            select(CachePolicy).where(CachePolicy.billing_plan_code == billing_plan_code)
        )
        return result.scalar_one_or_none()
    return None


async def get_exact(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    endpoint_type: str = "",
    model: str = "",
    request_hash: str = "",
    plan_code: str | None = None,
) -> CacheLookupResult:
    if not settings.response_cache_enabled:
        record_cache_result(
            hit=False, model=model, backend="cache", plan=plan_code, endpoint=endpoint_type
        )
        return CacheLookupResult(hit=False, cache_type="none")

    now = utc_now()
    stmt = select(ResponseCache).where(
        ResponseCache.cache_type == "exact",
        ResponseCache.endpoint_type == endpoint_type,
        ResponseCache.model == model,
        ResponseCache.request_hash == request_hash,
        ResponseCache.is_active.is_(True),
        ResponseCache.expires_at > now,
    )
    if client_id:
        stmt = stmt.where(
            or_(ResponseCache.client_id == client_id, ResponseCache.client_id.is_(None))
        )
    row = (await session.execute(stmt)).scalar_one_or_none()

    if row is None:
        record_cache_result(
            hit=False, model=model, backend="cache", plan=plan_code, endpoint=endpoint_type
        )
        return CacheLookupResult(hit=False, cache_type="none")

    row.hit_count += 1
    row.last_hit_at = now
    row.updated_at = now
    record_cache_result(
        hit=True, model=model, backend="cache", plan=plan_code, endpoint=endpoint_type
    )
    return CacheLookupResult(
        hit=True,
        payload=json.loads(row.response_json),
        prompt_tokens=row.prompt_tokens_estimated,
        completion_tokens=row.completion_tokens_estimated,
        cache_type="exact",
        cached_entry_id=str(row.id),
    )


async def set_exact(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    endpoint_type: str = "",
    model: str = "",
    provider: str | None = None,
    request_hash: str = "",
    request_fingerprint: str = "",
    prompt_fingerprint: str | None = None,
    normalized_prompt_hash: str | None = None,
    response_payload: dict,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    ttl_seconds: int | None = None,
    metadata: dict | None = None,
) -> None:
    if not settings.response_cache_enabled:
        return

    now = utc_now()
    ttl = ttl_seconds or settings.response_cache_ttl_seconds
    expires_at = now + timedelta(seconds=ttl)

    stmt = select(ResponseCache).where(
        ResponseCache.cache_type == "exact",
        ResponseCache.endpoint_type == endpoint_type,
        ResponseCache.model == model,
        ResponseCache.request_hash == request_hash,
    )
    if client_id:
        stmt = stmt.where(ResponseCache.client_id == client_id)

    row = (await session.execute(stmt)).scalar_one_or_none()

    if row is None:
        row = ResponseCache(
            cache_type="exact",
            client_id=client_id,
            endpoint_type=endpoint_type,
            model=model,
            provider=provider,
            request_hash=request_hash,
            request_fingerprint=request_fingerprint,
            prompt_fingerprint=prompt_fingerprint,
            normalized_prompt_hash=normalized_prompt_hash,
            response_json=json.dumps(response_payload, ensure_ascii=True),
            prompt_tokens_estimated=prompt_tokens,
            completion_tokens_estimated=completion_tokens,
            ttl_seconds=ttl,
            expires_at=expires_at,
            is_active=True,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return

    row.client_id = client_id
    row.request_fingerprint = request_fingerprint
    row.prompt_fingerprint = prompt_fingerprint
    row.normalized_prompt_hash = normalized_prompt_hash
    row.provider = provider
    row.response_json = json.dumps(response_payload, ensure_ascii=True)
    row.prompt_tokens_estimated = prompt_tokens
    row.completion_tokens_estimated = completion_tokens
    row.ttl_seconds = ttl
    row.expires_at = expires_at
    row.is_active = True
    row.metadata_json = json.dumps(metadata) if metadata else None
    row.updated_at = now


def _compute_semantic_embedding_id(normalized_prompt_hash: str) -> str:
    return hashlib.sha256(f"semantic:{normalized_prompt_hash}".encode()).hexdigest()


def _entry_to_embedding_vector(normalized_prompt_hash: str, dimensions: int = 64) -> list[float]:
    hex_seed = hashlib.sha256(normalized_prompt_hash.encode()).hexdigest()
    return _deterministic_embedding(hex_seed, dimensions=dimensions)


async def get_semantic(
    session: AsyncSession,
    *,
    client_id: str,
    endpoint_type: str = "",
    model: str = "",
    normalized_prompt_hash: str = "",
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    plan_code: str | None = None,
) -> CacheLookupResult:
    if not settings.semantic_cache_enabled:
        return CacheLookupResult(hit=False, cache_type="none")

    incoming_vector = _entry_to_embedding_vector(normalized_prompt_hash)
    now = utc_now()

    stmt = select(SemanticCacheEntry).where(
        SemanticCacheEntry.client_id == client_id,
        SemanticCacheEntry.endpoint_type == endpoint_type,
        SemanticCacheEntry.model == model,
        SemanticCacheEntry.is_active.is_(True),
        SemanticCacheEntry.expires_at > now,
    )
    rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        record_cache_result(
            hit=False, model=model, backend="semantic_cache", plan=plan_code, endpoint=endpoint_type
        )
        return CacheLookupResult(hit=False, cache_type="semantic")

    best_score = 0.0
    best_row = None
    for row in rows:
        stored_meta = {}
        if row.metadata_json:
            try:
                stored_meta = json.loads(row.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass
        stored_vector = stored_meta.get("embedding_vector")
        if stored_vector and len(stored_vector) == len(incoming_vector):
            score = _cosine_similarity(incoming_vector, stored_vector)
        else:
            score = 1.0 if row.normalized_prompt_hash == normalized_prompt_hash else 0.0

        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None or best_score < threshold:
        record_cache_result(
            hit=False, model=model, backend="semantic_cache", plan=plan_code, endpoint=endpoint_type
        )
        return CacheLookupResult(hit=False, cache_type="semantic", similarity_score=best_score)

    best_row.hit_count += 1
    best_row.last_hit_at = now
    best_row.updated_at = now
    record_cache_result(
        hit=True, model=model, backend="semantic_cache", plan=plan_code, endpoint=endpoint_type
    )
    return CacheLookupResult(
        hit=True,
        payload=json.loads(best_row.response_json),
        prompt_tokens=best_row.prompt_tokens_estimated,
        completion_tokens=best_row.completion_tokens_estimated,
        cache_type="semantic",
        similarity_score=best_score,
        cached_entry_id=str(best_row.id),
    )


async def set_semantic(
    session: AsyncSession,
    *,
    client_id: str,
    endpoint_type: str = "",
    model: str = "",
    provider: str | None = None,
    normalized_prompt_hash: str = "",
    response_payload: dict,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    ttl_seconds: int | None = None,
    metadata: dict | None = None,
) -> None:
    if not settings.semantic_cache_enabled:
        return

    embedding_vector = _entry_to_embedding_vector(normalized_prompt_hash)
    embedding_id = _compute_semantic_embedding_id(normalized_prompt_hash)
    now = utc_now()
    ttl = ttl_seconds or CACHE_TTL_24H
    expires_at = now + timedelta(seconds=ttl)

    meta = dict(metadata or {})
    meta["embedding_vector"] = embedding_vector
    meta["embedding_dimensions"] = len(embedding_vector)

    stmt = select(SemanticCacheEntry).where(
        SemanticCacheEntry.client_id == client_id,
        SemanticCacheEntry.endpoint_type == endpoint_type,
        SemanticCacheEntry.model == model,
        SemanticCacheEntry.semantic_embedding_id == embedding_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()

    if row is None:
        row = SemanticCacheEntry(
            client_id=client_id,
            endpoint_type=endpoint_type,
            model=model,
            provider=provider,
            normalized_prompt_hash=normalized_prompt_hash,
            semantic_embedding_id=embedding_id,
            response_json=json.dumps(response_payload, ensure_ascii=True),
            prompt_tokens_estimated=prompt_tokens,
            completion_tokens_estimated=completion_tokens,
            similarity_score=1.0,
            threshold_used=threshold,
            ttl_seconds=ttl,
            expires_at=expires_at,
            is_active=True,
            metadata_json=json.dumps(meta),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return

    row.response_json = json.dumps(response_payload, ensure_ascii=True)
    row.prompt_tokens_estimated = prompt_tokens
    row.completion_tokens_estimated = completion_tokens
    row.similarity_score = 1.0
    row.threshold_used = threshold
    row.ttl_seconds = ttl
    row.expires_at = expires_at
    row.is_active = True
    row.metadata_json = json.dumps(meta)
    row.updated_at = now


async def invalidate_client_cache(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    endpoint_type: str | None = None,
    model: str | None = None,
) -> dict:
    stmt_exact = delete(ResponseCache)
    stmt_semantic = delete(SemanticCacheEntry)
    conditions_exact = []
    conditions_semantic = []
    if client_id:
        conditions_exact.append(ResponseCache.client_id == client_id)
        conditions_semantic.append(SemanticCacheEntry.client_id == client_id)
    if endpoint_type:
        conditions_exact.append(ResponseCache.endpoint_type == endpoint_type)
        conditions_semantic.append(SemanticCacheEntry.endpoint_type == endpoint_type)
    if model:
        conditions_exact.append(ResponseCache.model == model)
        conditions_semantic.append(SemanticCacheEntry.model == model)
    if conditions_exact:
        stmt_exact = stmt_exact.where(and_(*conditions_exact))
    if conditions_semantic:
        stmt_semantic = stmt_semantic.where(and_(*conditions_semantic))

    exact_deleted = 0
    semantic_deleted = 0
    if not client_id and not endpoint_type and not model:
        exact_deleted = int((await session.execute(delete(ResponseCache))).rowcount or 0)
        semantic_deleted = int((await session.execute(delete(SemanticCacheEntry))).rowcount or 0)
    else:
        exact_deleted = int((await session.execute(stmt_exact)).rowcount or 0)
        semantic_deleted = int((await session.execute(stmt_semantic)).rowcount or 0)

    return {"exact_deleted": exact_deleted, "semantic_deleted": semantic_deleted}


async def cache_stats(session: AsyncSession) -> dict:
    now = utc_now()
    exact_rows = (
        (
            await session.execute(
                select(
                    func.count(ResponseCache.id).label("entries_total"),
                    func.count().filter(ResponseCache.expires_at <= now).label("expired_entries"),
                    func.coalesce(func.sum(ResponseCache.hit_count), 0).label("cache_reuses"),
                ).where(ResponseCache.cache_type == "exact")
            )
        )
        .mappings()
        .first()
    )

    semantic_rows = (
        (
            await session.execute(
                select(
                    func.count(SemanticCacheEntry.id).label("entries_total"),
                    func.count()
                    .filter(SemanticCacheEntry.expires_at <= now)
                    .label("expired_entries"),
                    func.coalesce(func.sum(SemanticCacheEntry.hit_count), 0).label("cache_reuses"),
                )
            )
        )
        .mappings()
        .first()
    )

    request_rows = (
        (
            await session.execute(
                select(
                    func.count(RequestLog.id).label("requests_total"),
                    func.count().filter(RequestLog.cache_hit.is_(True)).label("cache_hits_total"),
                )
            )
        )
        .mappings()
        .first()
    )

    requests_total = int(request_rows["requests_total"] or 0)
    cache_hits_total = int(request_rows["cache_hits_total"] or 0)

    return {
        "enabled": settings.response_cache_enabled,
        "semantic_cache_enabled": settings.semantic_cache_enabled,
        "ttl_seconds": settings.response_cache_ttl_seconds,
        "exact_entries": int(exact_rows["entries_total"] or 0),
        "semantic_entries": int(semantic_rows["entries_total"] or 0),
        "entries_total": int(exact_rows["entries_total"] or 0)
        + int(semantic_rows["entries_total"] or 0),
        "exact_expired": int(exact_rows["expired_entries"] or 0),
        "semantic_expired": int(semantic_rows["expired_entries"] or 0),
        "expired_entries": int(exact_rows["expired_entries"] or 0)
        + int(semantic_rows["expired_entries"] or 0),
        "exact_reuses": int(exact_rows["cache_reuses"] or 0),
        "semantic_reuses": int(semantic_rows["cache_reuses"] or 0),
        "cache_reuses": int(exact_rows["cache_reuses"] or 0)
        + int(semantic_rows["cache_reuses"] or 0),
        "requests_total": requests_total,
        "cache_hits_total": cache_hits_total,
        "cache_misses_total": max(requests_total - cache_hits_total, 0),
        "cache_hit_rate": round((cache_hits_total / requests_total), 4) if requests_total else 0.0,
    }


async def list_cache_entries(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    cache_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = (
        select(ResponseCache).order_by(ResponseCache.created_at.desc()).limit(limit).offset(offset)
    )
    if client_id:
        stmt = stmt.where(ResponseCache.client_id == client_id)
    if cache_type:
        stmt = stmt.where(ResponseCache.cache_type == cache_type)

    rows = (await session.execute(stmt)).scalars().all()
    result = []
    for row in rows:
        entry = {
            "id": str(row.id),
            "client_id": str(row.client_id) if row.client_id else None,
            "cache_type": row.cache_type,
            "endpoint_type": row.endpoint_type,
            "model": row.model,
            "provider": row.provider,
            "request_hash": row.request_hash[:16] + "...",
            "normalized_prompt_hash": row.normalized_prompt_hash[:16] + "..."
            if row.normalized_prompt_hash
            else None,
            "hit_count": row.hit_count,
            "ttl_seconds": row.ttl_seconds,
            "expires_at": row.expires_at.isoformat(),
            "last_hit_at": row.last_hit_at.isoformat() if row.last_hit_at else None,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat(),
        }
        result.append(entry)

    if cache_type == "semantic" or not cache_type:
        sstmt = (
            select(SemanticCacheEntry)
            .order_by(SemanticCacheEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if client_id:
            sstmt = sstmt.where(SemanticCacheEntry.client_id == client_id)
        srows = (await session.execute(sstmt)).scalars().all()
        for row in srows:
            entry = {
                "id": str(row.id),
                "client_id": str(row.client_id),
                "cache_type": "semantic",
                "endpoint_type": row.endpoint_type,
                "model": row.model,
                "provider": row.provider,
                "semantic_embedding_id": row.semantic_embedding_id[:16] + "...",
                "similarity_score": row.similarity_score,
                "threshold_used": row.threshold_used,
                "hit_count": row.hit_count,
                "ttl_seconds": row.ttl_seconds,
                "expires_at": row.expires_at.isoformat(),
                "last_hit_at": row.last_hit_at.isoformat() if row.last_hit_at else None,
                "is_active": row.is_active,
                "created_at": row.created_at.isoformat(),
            }
            result.append(entry)

    return result


async def get_cache_policies(session: AsyncSession) -> list[dict]:
    rows = (
        (await session.execute(select(CachePolicy).order_by(CachePolicy.created_at.desc())))
        .scalars()
        .all()
    )
    return [
        {
            "id": str(p.id),
            "client_id": str(p.client_id) if p.client_id else None,
            "billing_plan_code": p.billing_plan_code,
            "cache_enabled": p.cache_enabled,
            "semantic_cache_enabled": p.semantic_cache_enabled,
            "cache_ttl_seconds": p.cache_ttl_seconds,
            "cache_sensitive_data_allowed": p.cache_sensitive_data_allowed,
            "cache_price_discount_percent": p.cache_price_discount_percent,
            "max_cache_entries": p.max_cache_entries,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in rows
    ]


async def ensure_cache_policy(
    session: AsyncSession,
    *,
    client_id: str | None = None,
    billing_plan_code: str | None = None,
    cache_enabled: bool = True,
    semantic_cache_enabled: bool = False,
    cache_ttl_seconds: int = 3600,
    cache_sensitive_data_allowed: bool = False,
    cache_price_discount_percent: float = 100.0,
    max_cache_entries: int | None = None,
) -> CachePolicy:
    if client_id:
        existing = (
            await session.execute(select(CachePolicy).where(CachePolicy.client_id == client_id))
        ).scalar_one_or_none()
    elif billing_plan_code:
        existing = (
            await session.execute(
                select(CachePolicy).where(CachePolicy.billing_plan_code == billing_plan_code)
            )
        ).scalar_one_or_none()
    else:
        existing = None

    if existing:
        existing.cache_enabled = cache_enabled
        existing.semantic_cache_enabled = semantic_cache_enabled
        existing.cache_ttl_seconds = cache_ttl_seconds
        existing.cache_sensitive_data_allowed = cache_sensitive_data_allowed
        existing.cache_price_discount_percent = cache_price_discount_percent
        existing.max_cache_entries = max_cache_entries
        existing.updated_at = utc_now()
        return existing

    policy = CachePolicy(
        client_id=client_id,
        billing_plan_code=billing_plan_code,
        cache_enabled=cache_enabled,
        semantic_cache_enabled=semantic_cache_enabled,
        cache_ttl_seconds=cache_ttl_seconds,
        cache_sensitive_data_allowed=cache_sensitive_data_allowed,
        cache_price_discount_percent=cache_price_discount_percent,
        max_cache_entries=max_cache_entries,
    )
    session.add(policy)
    return policy
