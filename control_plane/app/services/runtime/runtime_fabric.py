import uuid
from datetime import UTC, datetime

from app.models.commercial.commercial_runtime_fabric import (
    CommercialRuntimeFabricEvent,
    CommercialRuntimeFabricHealth,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RuntimeFabricService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def report_heartbeat(self, node_id: str, status: str, metrics: dict):
        stmt = select(CommercialRuntimeFabricHealth).filter(
            CommercialRuntimeFabricHealth.node_id == node_id
        )
        result = await self.db.execute(stmt)
        health = result.scalars().first()

        if not health:
            health = CommercialRuntimeFabricHealth(id=str(uuid.uuid4()), node_id=node_id)
            self.db.add(health)

        health.status = status
        health.metrics = metrics
        health.last_check = datetime.now(UTC)

        # Check for anomalies
        if status != "healthy":
            await self._trigger_event(
                event_type="failure_detected",
                severity="critical" if status == "critical" else "warning",
                source_node_id=node_id,
                component="runtime",
                details={"status": status, "metrics": metrics},
            )

        await self.db.commit()
        return health

    async def _trigger_event(
        self, event_type: str, severity: str, source_node_id: str, component: str, details: dict
    ):
        event = CommercialRuntimeFabricEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            source_node_id=source_node_id,
            component=component,
            details=details,
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        return event

    async def get_fabric_health(self):
        stmt = select(CommercialRuntimeFabricHealth)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_events(self, limit: int = 100):
        stmt = (
            select(CommercialRuntimeFabricEvent)
            .order_by(CommercialRuntimeFabricEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
