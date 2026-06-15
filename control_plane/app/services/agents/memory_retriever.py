"""
Owner: agent-platform
Status: beta

Semantic memory retrieval with tenant isolation, consent, redaction, and scoring.
"""

import logging
import uuid
from datetime import UTC
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import AgentMemoryItem
from app.services.agents.memory_consent import MemoryConsentService
from app.services.agents.memory_indexing import MemoryIndexingService
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents.memory_redaction import MemoryRedactionService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MemoryRetrievalResult:
    def __init__(
        self,
        item: AgentMemoryItem,
        score: float,
        redacted: bool = False,
    ):
        self.item = item
        self.score = score
        self.redacted = redacted

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": str(self.item.id),
            "content": self.item.raw_content,
            "summary": self.item.summary,
            "score": round(self.score, 4),
            "memory_type": self.item.memory_type,
            "created_at": self.item.created_at.isoformat() if self.item.created_at else None,
        }


class MemoryRetriever:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.indexing = MemoryIndexingService(db)
        self.redaction = MemoryRedactionService(db)
        self.consent = MemoryConsentService(db)
        self.policy = MemoryPolicyService(db)

    async def retrieve(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        memory_type: str = "long_term",
        user_id: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[MemoryRetrievalResult]:
        semantic = self.settings.agent_memory_semantic_search_enabled

        items = await self.indexing.search(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query=query,
            limit=top_k * 3,
            semantic=semantic,
        )

        results: list[MemoryRetrievalResult] = []
        now = utc_now()
        for item in items:
            retention = item.retention_until
            if retention is not None:
                if retention.tzinfo is None:
                    retention = retention.replace(tzinfo=UTC)
                if retention <= now:
                    continue

            if item.memory_type != memory_type:
                continue

            if self.settings.agent_memory_consent_required and memory_type == "long_term":
                if user_id:
                    consent = await self.consent.get_consent(
                        tenant_id, user_id, memory_type, agent_id
                    )
                    if not consent:
                        continue

            raw_content = item.raw_content or ""
            redacted_types: list[str] = []

            search_policy = await self.policy.get_search_policy(tenant_id, agent_id, memory_type)
            if search_policy.get("redaction_enabled", True):
                raw_content, redacted_types = self.redaction.redact_content(raw_content)

            item.raw_content = raw_content

            score = 1.0
            if semantic and item.id:
                from app.models.agents.agents import AgentMemoryIndex
                from sqlalchemy.future import select

                stmt = select(AgentMemoryIndex).where(
                    AgentMemoryIndex.memory_item_id == item.id,
                    AgentMemoryIndex.tenant_id == tenant_id,
                )
                res = await self.db.execute(stmt)
                idx = res.scalar_one_or_none()
                if idx and idx.embedding:
                    import json
                    import math

                    query_emb = await self.indexing._compute_embedding(query)
                    try:
                        item_emb = json.loads(idx.embedding)
                        dot = sum(x * y for x, y in zip(query_emb, item_emb))
                        nq = math.sqrt(sum(x * x for x in query_emb))
                        ni = math.sqrt(sum(y * y for y in item_emb))
                        if nq > 0 and ni > 0:
                            score = dot / (nq * ni)
                    except (json.JSONDecodeError, TypeError, ZeroDivisionError):
                        score = 1.0

            if score < score_threshold:
                continue

            if self._contains_secrets(raw_content) and memory_type != "short_term":
                logger.warning(f"Skipping memory {item.id} with potential secrets")
                continue

            result = MemoryRetrievalResult(
                item=item,
                score=score,
                redacted=bool(redacted_types),
            )
            results.append(result)

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _contains_secrets(self, text: str) -> bool:
        patterns = ["sk-", "api_", "key_", "passwd", "password", "secret"]
        for p in patterns:
            if p in text.lower():
                return True
        return False
