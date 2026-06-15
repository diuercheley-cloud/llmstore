import uuid
from datetime import UTC, datetime

from app.models.commercial.commercial_runtime_fabric import (
    CommercialRuntimeDeterminismDrift,
    CommercialRuntimeFabricEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class DeterminismRepairService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def report_drift(
        self,
        workflow_id: str,
        step_index: int,
        expected_hash: str,
        actual_hash: str,
        drift_details: dict,
    ):
        drift = CommercialRuntimeDeterminismDrift(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            step_index=step_index,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            drift_details=drift_details,
            detected_at=datetime.now(UTC),
        )
        self.db.add(drift)

        # Trigger an event for the fabric
        event = CommercialRuntimeFabricEvent(
            id=str(uuid.uuid4()),
            event_type="drift_detected",
            severity="warning",
            source_node_id="fabric-monitor",
            component="workflow",
            details={"workflow_id": workflow_id, "step_index": step_index, "drift_id": drift.id},
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.commit()
        return drift

    async def mark_repaired(self, drift_id: str, repair_plan_id: str):
        stmt = select(CommercialRuntimeDeterminismDrift).filter(
            CommercialRuntimeDeterminismDrift.id == drift_id
        )
        result = await self.db.execute(stmt)
        drift = result.scalars().first()
        if not drift:
            raise ValueError("Drift record not found")

        drift.repaired_at = datetime.now(UTC)
        drift.repair_plan_id = repair_plan_id
        await self.db.commit()
        return drift

    async def get_active_drifts(self):
        stmt = select(CommercialRuntimeDeterminismDrift).filter(
            CommercialRuntimeDeterminismDrift.repaired_at == None
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
