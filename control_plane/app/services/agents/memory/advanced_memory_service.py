import hashlib
import json
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.advanced_memory import (
    MemoryEvent,
    MemoryEventType,
    MemoryScope,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AdvancedMemoryService:
    def __init__(self, db: AsyncSession, node_id: str = "node-0"):
        self.db = db
        self.node_id = node_id

    async def append_event(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        scope: MemoryScope,
        event_type: MemoryEventType,
        payload: dict[str, Any],
        importance_score: float = 1.0,
    ) -> MemoryEvent:
        # 1. Get previous event for hash chain
        stmt = (
            select(MemoryEvent)
            .where(MemoryEvent.agent_id == agent_id, MemoryEvent.scope == scope)
            .order_by(MemoryEvent.logical_counter.desc(), MemoryEvent.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        prev_event = result.scalar_one_or_none()

        prev_hash = prev_event.event_hash if prev_event else None
        prev_counter = prev_event.logical_counter if prev_event else 0

        # 2. Compute hashes
        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        event_data = f"{prev_hash}|{payload_hash}|{event_type}|{str(agent_id)}|{prev_counter + 1}"
        event_hash = hashlib.sha256(event_data.encode()).hexdigest()

        # 3. Create event
        event = MemoryEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            scope=scope,
            event_type=event_type,
            payload=payload,
            payload_hash=payload_hash,
            previous_event_hash=prev_hash,
            event_hash=event_hash,
            node_id=self.node_id,
            logical_counter=prev_counter + 1,
            importance_score=importance_score,
            decay_score=0.0,  # Will be updated by forgetting curve logic
        )

        self.db.add(event)
        await self.db.flush()
        return event

    async def access_memory(self, event_id: uuid.UUID):
        """Update access metrics for forgetting curve."""
        stmt = (
            update(MemoryEvent)
            .where(MemoryEvent.id == event_id)
            .values(access_count=MemoryEvent.access_count + 1, last_accessed_at=utc_now())
        )
        await self.db.execute(stmt)

    async def compute_forgetting_scores(self, agent_id: uuid.UUID):
        """
        Updates decay scores based on a simple forgetting curve:
        Score = Importance / (1 + log(1 + time_since_last_access)) * (1 + log(1 + access_count))
        """
        stmt = select(MemoryEvent).where(MemoryEvent.agent_id == agent_id)
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        now = utc_now()
        for event in events:
            last_access = event.last_accessed_at or event.created_at
            hours_since = (now - last_access).total_seconds() / 3600

            # Simple decay model
            # Higher score means more "memorable"
            import math

            recency_factor = 1.0 / (1.0 + math.log(1.0 + hours_since))
            frequency_factor = 1.0 + math.log(1.0 + event.access_count)

            event.decay_score = event.importance_score * recency_factor * frequency_factor

        await self.db.flush()

    async def list_memories(
        self, agent_id: uuid.UUID, scope: MemoryScope | None = None
    ) -> list[MemoryEvent]:
        query = select(MemoryEvent).where(MemoryEvent.agent_id == agent_id)
        if scope:
            query = query.where(MemoryEvent.scope == scope)
        query = query.order_by(MemoryEvent.decay_score.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def redact_memory(self, event_id: uuid.UUID, reason: str):
        stmt = select(MemoryEvent).where(MemoryEvent.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()

        if event:
            await self.append_event(
                tenant_id=event.tenant_id,
                agent_id=event.agent_id,
                scope=event.scope,
                event_type=MemoryEventType.REDACTED,
                payload={
                    "target_event_id": str(event_id),
                    "reason": reason,
                    "original_type": event.event_type,
                },
            )
            # Mask the original payload
            event.payload = {"status": "redacted", "reason": reason}
            await self.db.flush()

    async def forget_memory(self, event_id: uuid.UUID):
        """Mark a memory event as forgotten."""
        stmt = select(MemoryEvent).where(MemoryEvent.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()

        if event:
            await self.append_event(
                tenant_id=event.tenant_id,
                agent_id=event.agent_id,
                scope=event.scope,
                event_type=MemoryEventType.FORGOTTEN,
                payload={"target_event_id": str(event_id)},
            )
            # Remove from active memories by setting importance to 0
            event.importance_score = 0.0
            event.decay_score = 0.0
            await self.db.flush()

    async def get_memory_events(self, agent_id: uuid.UUID) -> list[MemoryEvent]:
        stmt = (
            select(MemoryEvent)
            .where(MemoryEvent.agent_id == agent_id)
            .order_by(MemoryEvent.logical_counter.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
