import hashlib
import uuid
from typing import Any, Dict, List

from app.core.time import utc_now
from app.models.agents.web_search import AgentWebSearchQuery, AgentWebSearchResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SearchAuditService:
    def get_query_hash(self, query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    async def log_search(
        self,
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
        query: str,
        provider: str,
        results: List[Dict[str, Any]],
    ) -> AgentWebSearchQuery:
        query_hash = self.get_query_hash(query)

        query_record = AgentWebSearchQuery(
            id=uuid.uuid4(),
            run_id=run_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            query=query,
            query_hash=query_hash,
            provider=provider,
            created_at=utc_now(),
        )
        db.add(query_record)
        await db.flush()

        for r in results:
            res_rec = AgentWebSearchResult(
                id=uuid.uuid4(),
                query_id=query_record.id,
                title=r.get("title", ""),
                snippet=r.get("snippet", ""),
                url=r.get("url", ""),
                confidence=r.get("confidence", 1.0),
                retrieved_at=r.get("retrieved_at") or utc_now(),
            )
            db.add(res_rec)

        await db.commit()
        await db.refresh(query_record)
        return query_record

    async def get_audit_trail(self, db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = (
            select(AgentWebSearchQuery)
            .options(selectinload(AgentWebSearchQuery.results))
            .order_by(AgentWebSearchQuery.created_at.desc())
        )
        res = await db.execute(stmt)
        queries = res.scalars().all()

        audit_trail = []
        for q in queries:
            audit_trail.append(
                {
                    "id": str(q.id),
                    "run_id": str(q.run_id) if q.run_id else None,
                    "agent_id": str(q.agent_id) if q.agent_id else None,
                    "tenant_id": q.tenant_id,
                    "query": q.query,
                    "query_hash": q.query_hash,
                    "provider": q.provider,
                    "created_at": q.created_at.isoformat(),
                    "results": [
                        {
                            "id": str(r.id),
                            "title": r.title,
                            "snippet": r.snippet,
                            "url": r.url,
                            "confidence": r.confidence,
                            "retrieved_at": r.retrieved_at.isoformat(),
                        }
                        for r in q.results
                    ],
                }
            )
        return audit_trail
