import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.time import utc_now
from app.models.web_search import AgentWebSearchCache
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SearchCacheService:
    async def get_cached_results(
        self, db: AsyncSession, query_hash: str
    ) -> Optional[List[Dict[str, Any]]]:
        stmt = select(AgentWebSearchCache).where(
            AgentWebSearchCache.query_hash == query_hash
        )
        res = await db.execute(stmt)
        cache_entry = res.scalar_one_or_none()

        if not cache_entry:
            return None

        # Check TTL expiration
        expires_at = cache_entry.created_at + timedelta(
            seconds=cache_entry.ttl_seconds
        )
        now = utc_now()
        if expires_at.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif expires_at.tzinfo is not None and now.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=None)
        if now > expires_at:
            await db.delete(cache_entry)
            await db.commit()
            return None

        results = cache_entry.results_json
        for r in results:
            if "retrieved_at" in r and isinstance(r["retrieved_at"], str):
                try:
                    r["retrieved_at"] = datetime.fromisoformat(r["retrieved_at"])
                except Exception:
                    pass
        return results

    async def save_to_cache(
        self,
        db: AsyncSession,
        query_hash: str,
        results: List[Dict[str, Any]],
        ttl_seconds: int = 3600,
    ) -> None:
        # Clear existing cached results for the hash first
        stmt = select(AgentWebSearchCache).where(
            AgentWebSearchCache.query_hash == query_hash
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.commit()

        # Serialize datetimes to string for JSON field storage
        serialized_results = []
        for r in results:
            item = dict(r)
            if "retrieved_at" in item and isinstance(item["retrieved_at"], datetime):
                item["retrieved_at"] = item["retrieved_at"].isoformat()
            serialized_results.append(item)

        cache_entry = AgentWebSearchCache(
            id=uuid.uuid4(),
            query_hash=query_hash,
            results_json=serialized_results,
            ttl_seconds=ttl_seconds,
            created_at=utc_now(),
        )
        db.add(cache_entry)
        await db.commit()

    async def list_cache_entries(self, db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(AgentWebSearchCache)
        res = await db.execute(stmt)
        entries = res.scalars().all()
        return [
            {
                "id": str(e.id),
                "query_hash": e.query_hash,
                "ttl_seconds": e.ttl_seconds,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]
