import json
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents.immutable_audit import ImmutableAuditLog
from .contracts import AuditRepository, AuditEntryData
from app.core.time import utc_now

class SqlAlchemyAuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _compute_record_hash(self, action: str, actor: str, payload_str: str, timestamp_str: str, previous_hash: Optional[str]) -> str:
        prev = previous_hash or ""
        raw_data = f"{action}|{actor}|{payload_str}|{timestamp_str}|{prev}"
        return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

    async def record_event(self, entry: AuditEntryData, signature: Optional[str] = None) -> str:
        # 1. Fetch last entry for previous hash
        stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.desc()).limit(1)
        res = await self.db.execute(stmt)
        last_entry = res.scalar_one_or_none()
        previous_hash = last_entry.hash if last_entry else None

        # 2. Prepare data
        payload_str = json.dumps(entry.payload, sort_keys=True)
        timestamp_str = entry.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")

        # 3. Compute hash
        record_hash = self._compute_record_hash(
            entry.action, entry.actor, payload_str, timestamp_str, previous_hash
        )

        # 4. Save
        log = ImmutableAuditLog(
            tenant_id=entry.tenant_id,
            action=entry.action,
            actor=entry.actor,
            payload=payload_str,
            previous_hash=previous_hash,
            hash=record_hash,
            signature=signature or f"unsigned:{record_hash}",
            created_at=entry.timestamp
        )
        self.db.add(log)
        await self.db.flush()
        return record_hash

    async def list_events(self, limit: int = 100) -> List[AuditEntryData]:
        result = await self.db.execute(
            select(ImmutableAuditLog).order_by(ImmutableAuditLog.created_at.desc()).limit(limit)
        )
        logs = result.scalars().all()
        return [
            AuditEntryData(
                id=str(l.id),
                timestamp=l.created_at,
                action=l.action,
                actor=l.actor,
                payload=json.loads(l.payload),
                tenant_id=l.tenant_id
            ) for l in logs
        ]

    async def get_event_by_id(self, event_id: str) -> Optional[AuditEntryData]:
        try:
            eid = int(event_id)
        except ValueError:
            return None
            
        result = await self.db.execute(select(ImmutableAuditLog).where(ImmutableAuditLog.id == eid))
        l = result.scalar_one_or_none()
        if not l:
            return None
        return AuditEntryData(
            id=str(l.id),
            timestamp=l.created_at,
            action=l.action,
            actor=l.actor,
            payload=json.loads(l.payload),
            tenant_id=l.tenant_id
        )

    async def get_last_hash(self) -> Optional[str]:
        stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.desc()).limit(1)
        res = await self.db.execute(stmt)
        last_entry = res.scalar_one_or_none()
        return last_entry.hash if last_entry else None
