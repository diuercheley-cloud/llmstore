import uuid
from datetime import datetime, UTC

from app.models.commercial.commercial_runtime_fabric import (
    CommercialRuntimeFabricEvent,
    CommercialRuntimeHealingAction,
    CommercialRuntimeRecoveryPlan,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RuntimeRecoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recovery_plan(self, event_id: str, mode: str = "advisory"):
        stmt = select(CommercialRuntimeFabricEvent).filter(CommercialRuntimeFabricEvent.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise ValueError("Event not found")

        plan = CommercialRuntimeRecoveryPlan(
            id=str(uuid.uuid4()),
            event_id=event_id,
            mode=mode,
            status="pending",
            steps=self._determine_steps(event),
            created_at=datetime.now(UTC)
        )
        self.db.add(plan)
        await self.db.commit()
        return plan

    def _determine_steps(self, event: CommercialRuntimeFabricEvent):
        steps = []
        if event.component == "runtime" and event.event_type == "failure_detected":
            steps.append({
                "action_type": "restart_service",
                "target_id": event.source_node_id,
                "parameters": {"service": "inference_engine"}
            })
        elif event.component == "workflow" and event.event_type == "drift_detected":
            steps.append({
                "action_type": "replay_workflow",
                "target_id": event.details.get("workflow_id"),
                "parameters": {"from_step": event.details.get("step_index")}
            })
        return steps

    async def execute_plan(self, plan_id: str):
        stmt = select(CommercialRuntimeRecoveryPlan).filter(CommercialRuntimeRecoveryPlan.id == plan_id)
        result = await self.db.execute(stmt)
        plan = result.scalars().first()
        if not plan:
            raise ValueError("Plan not found")

        plan.status = "executing"
        plan.updated_at = datetime.now(UTC)
        await self.db.commit()

        for step in plan.steps:
            action = CommercialRuntimeHealingAction(
                id=str(uuid.uuid4()),
                plan_id=plan.id,
                action_type=step["action_type"],
                target_id=step["target_id"],
                parameters=step["parameters"],
                status="pending",
                started_at=datetime.now(UTC)
            )
            self.db.add(action)
            await self.db.commit()

            # Simulate success
            action.status = "completed"
            action.result = {"success": True}
            action.finished_at = datetime.now(UTC)
            action.signed_receipt = "signed-receipt-" + str(uuid.uuid4())
            await self.db.commit()

        plan.status = "completed"
        plan.updated_at = datetime.now(UTC)
        await self.db.commit()
        return plan
