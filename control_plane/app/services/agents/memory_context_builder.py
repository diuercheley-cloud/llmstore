"""
Owner: agent-platform
Status: beta

Builds a "Relevant Memory" context block for reinjection into the LLM prompt.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.agents.memory_retriever import MemoryRetrievalResult, MemoryRetriever
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MemoryContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.retriever = MemoryRetriever(db)

    async def build_context(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        user_id: Optional[str] = None,
        memory_type: str = "long_term",
        max_tokens: int = 2048,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        if not self.settings.agent_memory_context_injection_enabled:
            return {"context_block": "", "memory_ids": [], "total_tokens": 0}

        memories = await self.retriever.retrieve(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query=query,
            memory_type=memory_type,
            user_id=user_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        return self._build_block(memories, max_tokens)

    def _build_block(
        self,
        memories: List[MemoryRetrievalResult],
        max_tokens: int,
    ) -> Dict[str, Any]:
        if not memories:
            return {"context_block": "", "memory_ids": [], "total_tokens": 0}

        lines: List[str] = []
        memory_ids: List[str] = []
        total_tokens = 0

        for mem in memories:
            content = mem.item.raw_content or ""
            summary = mem.item.summary or ""
            mem_tokens = estimate_tokens(content) + estimate_tokens(summary)

            if total_tokens + mem_tokens > max_tokens:
                continue

            line = f"- {summary}: {content}" if summary else f"- {content}"
            lines.append(line)
            memory_ids.append(str(mem.item.id))
            total_tokens += mem_tokens

        if not lines:
            return {"context_block": "", "memory_ids": [], "total_tokens": 0}

        context_block = (
            "## Relevant Memory\n"
            "The following information was retrieved from the agent's long-term memory:\n"
            + "\n".join(lines)
        )

        return {
            "context_block": context_block,
            "memory_ids": memory_ids,
            "total_tokens": total_tokens,
        }
