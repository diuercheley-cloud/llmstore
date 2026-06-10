import json
import uuid

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session, get_redis
from app.services.auth import require_admin
from app.services.cache.intelligent_cache import (
    cache_stats as intelligent_cache_stats,
    ensure_cache_policy,
    get_cache_policies,
    invalidate_client_cache,
    list_cache_entries,
)
from app.services.response_cache import clear_response_cache
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin-cache"], dependencies=[Depends(require_admin)])


class CachePolicyCreate(BaseModel):
    client_id: str | None = None
    billing_plan_code: str | None = None
    cache_enabled: bool = True
    semantic_cache_enabled: bool = False
    cache_ttl_seconds: int = 3600
    cache_sensitive_data_allowed: bool = False
    cache_price_discount_percent: float = 100.0
    max_cache_entries: int | None = None


@router.get("/cache/stats")
async def cache_stats(session: AsyncSession = Depends(get_db_session)):
    return await intelligent_cache_stats(session)


@router.get("/cache/entries")
async def cache_entries(
    client_id: str | None = None,
    cache_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    return await list_cache_entries(session, client_id=client_id, cache_type=cache_type, limit=limit, offset=offset)


@router.post("/cache/invalidate")
async def cache_invalidate(
    client_id: str | None = None,
    endpoint_type: str | None = None,
    model: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    result = await invalidate_client_cache(session, client_id=client_id, endpoint_type=endpoint_type, model=model)
    await session.commit()
    return result


@router.get("/cache/policies")
async def cache_policies(session: AsyncSession = Depends(get_db_session)):
    return await get_cache_policies(session)


@router.post("/cache/policies", status_code=status.HTTP_201_CREATED)
async def create_cache_policy(payload: CachePolicyCreate, session: AsyncSession = Depends(get_db_session)):
    policy = await ensure_cache_policy(
        session,
        client_id=payload.client_id,
        billing_plan_code=payload.billing_plan_code,
        cache_enabled=payload.cache_enabled,
        semantic_cache_enabled=payload.semantic_cache_enabled,
        cache_ttl_seconds=payload.cache_ttl_seconds,
        cache_sensitive_data_allowed=payload.cache_sensitive_data_allowed,
        cache_price_discount_percent=payload.cache_price_discount_percent,
        max_cache_entries=payload.max_cache_entries,
    )
    await session.commit()
    return policy


@router.delete("/cache/responses")
async def cache_clear(session: AsyncSession = Depends(get_db_session)):
    deleted = await clear_response_cache(session)
    await session.commit()
    return {"deleted": deleted, "status": "cleared"}
