import uuid
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, List, Optional, Dict
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentMemoryItem,
    AgentMemoryAccessEvent,
    AgentMemoryPolicy,
    AgentMemoryCollection,
)
from app.services.agents.memory_policy import MemoryPolicyService
from app.services.agents.memory_consent import MemoryConsentService
from app.services.agents.memory_redaction import MemoryRedactionService
from app.services.agents.memory_indexing import MemoryIndexingService
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class MemoryDisabledError(RuntimeError):
    pass

class SecretFoundError(ValueError):
    pass

class ConsentRequiredError(ValueError):
    pass

class AgentMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.policy_service = MemoryPolicyService(db)
        self.consent_service = MemoryConsentService(db)
        self.redaction_service = MemoryRedactionService(db)
        self.indexing_service = MemoryIndexingService(db)

    def _check_enabled(self):
        if not self.settings.agent_memory_enabled:
            raise MemoryDisabledError("Agent memory is disabled globally.")

    def _contains_secrets(self, text: str) -> bool:
        # Simple heuristic for secrets
        patterns = ["sk-", "api_", "key_", "passwd", "password", "secret"]
        for p in patterns:
            if p in text.lower():
                return True
        return False

    async def _log_access(self, tenant_id: str, agent_id: uuid.UUID, item_id: uuid.UUID, operation: str, run_id: Optional[uuid.UUID] = None):
        event = AgentMemoryAccessEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            memory_item_id=item_id,
            operation=operation
        )
        self.db.add(event)

    async def write_memory(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_type: str,
        content: str,
        user_id: Optional[str] = None,
        summary: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        collection_id: Optional[uuid.UUID] = None
    ) -> AgentMemoryItem:
        self._check_enabled()
        if not self.settings.agent_memory_write_enabled:
            raise MemoryDisabledError("Memory write is disabled.")

        if memory_type == "long_term" and not self.settings.agent_long_term_memory_enabled:
            raise MemoryDisabledError("Long-term memory is disabled.")

        if self.settings.agent_memory_consent_required and memory_type == "long_term":
            if not user_id:
                raise ConsentRequiredError("user_id must be provided when consent is required.")
            consent = await self.consent_service.get_consent(tenant_id, user_id, memory_type, agent_id)
            if not consent:
                raise ConsentRequiredError(f"No active consent found for user {user_id} and memory type {memory_type}.")

        if self._contains_secrets(content):
            raise SecretFoundError("Potential secret detected in memory content. Blocking persistence.")

        policy = await self.policy_service.get_policy(tenant_id, agent_id, memory_type)
        if not policy:
            raise ValueError(f"No retention policy found for memory type '{memory_type}' and tenant '{tenant_id}'.")

        # Redaction
        redaction_status = "none"
        final_content = content
        redacted_types = []
        if policy.redaction_enabled:
            final_content, redacted_types = self.redaction_service.redact_content(content)
            if redacted_types:
                redaction_status = "completed"

        retention_until = utc_now() + timedelta(days=policy.retention_days)
        
        item = AgentMemoryItem(
            tenant_id=tenant_id,
            agent_id=agent_id,
            collection_id=collection_id,
            memory_type=memory_type,
            content_hash=agent_state.compute_sha256(final_content),
            raw_content=final_content,
            summary=summary,
            source_run_id=run_id,
            provenance={"created_at": utc_now().isoformat(), "source": "agent_run", "run_id": str(run_id) if run_id else None},
            retention_until=retention_until,
            redaction_status=redaction_status
        )
        
        self.db.add(item)
        await self.db.flush()
        
        if redacted_types:
            await self.redaction_service.log_redaction(tenant_id, agent_id, item.id, redacted_types)
        
        await self._log_access(tenant_id, agent_id, item.id, "write", run_id)
        
        # Async indexing trigger
        await self.indexing_service.index_item(tenant_id, agent_id, item)
        
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def read_memory(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_type: Optional[str] = None,
        collection_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        run_id: Optional[uuid.UUID] = None
    ) -> List[AgentMemoryItem]:
        self._check_enabled()
        
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.tenant_id == tenant_id,
            AgentMemoryItem.agent_id == agent_id,
            AgentMemoryItem.retention_until > utc_now()
        )
        
        if memory_type:
            stmt = stmt.where(AgentMemoryItem.memory_type == memory_type)
        if collection_id:
            stmt = stmt.where(AgentMemoryItem.collection_id == collection_id)
            
        stmt = stmt.order_by(AgentMemoryItem.created_at.desc()).limit(limit)
        
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        
        for item in items:
            item.last_accessed_at = utc_now()
            await self._log_access(tenant_id, agent_id, item.id, "read", run_id)
            
        await self.db.commit()
        return items

    async def delete_memory_item(self, tenant_id: str, item_id: uuid.UUID):
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.id == item_id,
            AgentMemoryItem.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        
        if not item:
            raise ValueError("Memory item not found or tenant mismatch.")
            
        await self._log_access(tenant_id, item.agent_id, item.id, "delete")
        await self.db.delete(item)
        await self.db.commit()

    async def export_memory(self, tenant_id: str, agent_id: Optional[uuid.UUID] = None, memory_type: Optional[str] = None) -> List[dict]:
        if not self.settings.agent_memory_export_enabled:
            raise MemoryDisabledError("Memory export is disabled.")
            
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.tenant_id == tenant_id,
            AgentMemoryItem.retention_until > utc_now()
        )
        if agent_id:
            stmt = stmt.where(AgentMemoryItem.agent_id == agent_id)
        if memory_type:
            stmt = stmt.where(AgentMemoryItem.memory_type == memory_type)
            
        res = await self.db.execute(stmt)
        items = res.scalars().all()
        
        export_data = []
        for item in items:
            # Re-check for secrets on export just in case
            if self._contains_secrets(item.raw_content):
                continue
                
            await self._log_access(tenant_id, item.agent_id, item.id, "export")
            export_data.append({
                "id": str(item.id),
                "agent_id": str(item.agent_id),
                "type": item.memory_type,
                "content": item.raw_content,
                "summary": item.summary,
                "created_at": item.created_at.isoformat()
            })
            
        await self.db.commit()
        return export_data

    async def search_memory(self, tenant_id: str, agent_id: uuid.UUID, query: str, limit: int = 10) -> List[AgentMemoryItem]:
        self._check_enabled()
        if not self.settings.agent_memory_search_enabled:
            raise MemoryDisabledError("Memory search is disabled.")
            
        return await self.indexing_service.search(tenant_id, agent_id, query, limit)
