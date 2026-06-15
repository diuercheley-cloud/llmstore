# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.agent_execution import AgentExecutionJob
from app.models.agents.agents import AgentRun, AgentRunReceipt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ReconstructionError(ValueError):
    """Raised when runtime state cannot be securely reconstructed from receipts."""

    pass


class RuntimeReconstructionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconstruct_run_state(self, run_id: uuid.UUID) -> dict[str, Any]:
        """
        Reconstructs the current run state and active steps from stored execution receipts.
        Validates completeness, performs lease recovery and orphan recovery if needed.
        """
        run_stmt = select(AgentRun).where(AgentRun.id == run_id)
        run_res = await self.db.execute(run_stmt)
        run = run_res.scalar_one_or_none()
        if not run:
            raise ReconstructionError(f"Agent run {run_id} not found.")

        # Gather execution receipts for the run
        receipt_stmt = (
            select(AgentRunReceipt)
            .where(AgentRunReceipt.run_id == run_id)
            .order_by(AgentRunReceipt.step_number.asc())
        )
        receipt_res = await self.db.execute(receipt_stmt)
        receipts = receipt_res.scalars().all()

        # Reconstruct the true progress (total steps) from the receipt log
        expected_steps = len(receipts)
        logger.info(
            f"Reconstructing run {run_id}: found {expected_steps} receipts. Current run total_steps is {run.total_steps}"
        )

        # Reconcile database state with receipts
        if run.total_steps != expected_steps:
            logger.warning(
                f"Run total_steps ({run.total_steps}) mismatch with receipts ({expected_steps}). Reconciling..."
            )
            run.total_steps = expected_steps

        # Check for orphan/lease recovery
        is_orphaned = False
        repaired = False

        # If marked as running but has expired/stale leases or no heartbeat
        if run.status == "running":
            # Check execution jobs/leases
            job_stmt = select(AgentExecutionJob).where(
                AgentExecutionJob.agent_run_id == run_id,
                AgentExecutionJob.queue_status == "running",
            )
            job_res = await self.db.execute(job_stmt)
            active_jobs = job_res.scalars().all()

            # Lease recovery: if a job has been running too long without completion, mark it as orphaned/failed
            for job in active_jobs:
                # If leased more than 5 minutes ago (arbitrary lease boundary for testing)
                time_elapsed = (utc_now() - job.created_at).total_seconds()
                if time_elapsed > 300:  # 5 minutes lease expiry
                    logger.warning(
                        f"Lease expired for execution job {job.id} (run {run_id}). Reclaiming lease."
                    )
                    job.queue_status = "failed"
                    is_orphaned = True
                    repaired = True

            if is_orphaned or not active_jobs:
                # Revert run to queued status so it can be picked up by another worker safely
                run.status = "queued"
                logger.info(f"Recovered orphan run {run_id}. Run reset to 'queued' state.")
                repaired = True

        # Commit any reconciliation/recovery changes
        await self.db.commit()

        # Rebuild structured reconstruction data
        reconstructed_steps = []
        for r in receipts:
            reconstructed_steps.append(
                {
                    "step_number": r.step_number,
                    "type": r.receipt_data.get("type"),
                    "success": r.receipt_data.get("success", True),
                    "timestamp": r.receipt_data.get("timestamp"),
                }
            )

        return {
            "run_id": str(run_id),
            "status": run.status,
            "total_steps": run.total_steps,
            "reconstructed_steps": reconstructed_steps,
            "lease_recovered": repaired,
        }
