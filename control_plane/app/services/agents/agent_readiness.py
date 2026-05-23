import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentRun, AgentIncident, AgentDefinition, AgentMemoryPolicy, AgentApprovalRequest
from app.models.agent_execution import (
    AgentWorkerHeartbeat,
    AgentExecutionJob,
    AgentExecutionLease,
    AgentExecutionDeadLetter,
)
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class ReadinessStatus(str, Enum):
    DISABLED = "disabled"
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"

class AgentReadinessService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def check_readiness(self) -> Dict[str, Any]:
        results = {
            "status": ReadinessStatus.READY,
            "timestamp": utc_now().isoformat(),
            "checks": [],
            "blockers": [],
            "warnings": [],
            "recommendations": []
        }

        # 1. Runtime Enabled Check (CRITICAL)
        runtime_enabled = self.settings.agent_runtime_enabled
        if not runtime_enabled:
            results["status"] = ReadinessStatus.DISABLED
            results["checks"].append({
                "id": "runtime_enabled",
                "name": "Agent Runtime Enabled",
                "status": "fail",
                "value": False,
                "message": "Agent Runtime is globally disabled."
            })
            results["blockers"].append("AGENT_RUNTIME_ENABLED is false")
            results["recommendations"].append("Set AGENT_RUNTIME_ENABLED=true in environment.")
            # If disabled, we stop some checks or proceed with caution
        else:
            results["checks"].append({
                "id": "runtime_enabled",
                "name": "Agent Runtime Enabled",
                "status": "pass",
                "value": True
            })

        # 2. Execution Plane Check
        plane_enabled = self.settings.agent_execution_plane_enabled
        results["checks"].append({
            "id": "execution_plane",
            "name": "Execution Plane Enabled",
            "status": "pass" if plane_enabled else "warn",
            "value": plane_enabled
        })
        if not plane_enabled and runtime_enabled:
            results["warnings"].append("Execution Plane is disabled; agents won't execute.")

        # 3. Worker Heartbeat (if worker enabled)
        if self.settings.agent_worker_enabled:
            res_workers = await self.db.execute(
                select(func.count(AgentWorkerHeartbeat.worker_id))
                .where(AgentWorkerHeartbeat.last_heartbeat >= utc_now() - timedelta(minutes=2))
            )
            active_workers = res_workers.scalar() or 0
            worker_status = "pass" if active_workers > 0 else "fail"
            results["checks"].append({
                "id": "worker_heartbeat",
                "name": "Active Workers Heartbeat",
                "status": worker_status,
                "value": active_workers,
                "message": f"{active_workers} active workers in the last 2 minutes."
            })
            if active_workers == 0:
                results["blockers"].append("No active agent workers detected while AGENT_WORKER_ENABLED is true.")
                results["status"] = ReadinessStatus.BLOCKED if results["status"] != ReadinessStatus.DISABLED else results["status"]

        # 4. Queue Depth and Stuck Runs
        res_queue = await self.db.execute(select(func.count(AgentExecutionJob.id)).where(AgentExecutionJob.status == "queued"))
        queue_depth = res_queue.scalar() or 0
        results["checks"].append({
            "id": "queue_depth",
            "name": "Execution Queue Depth",
            "status": "pass" if queue_depth < 50 else "warn",
            "value": queue_depth
        })

        res_stuck = await self.db.execute(
            select(func.count(AgentRun.id))
            .where(AgentRun.status == "running")
            .where(AgentRun.started_at <= utc_now() - timedelta(hours=1))
        )
        stuck_runs = res_stuck.scalar() or 0
        if stuck_runs > 0:
            results["checks"].append({
                "id": "stuck_runs",
                "name": "Stuck Agent Runs",
                "status": "fail",
                "value": stuck_runs,
                "message": f"Detected {stuck_runs} runs stuck in 'running' state for > 1 hour."
            })
            results["warnings"].append(f"{stuck_runs} stuck runs detected")
            if results["status"] == ReadinessStatus.READY:
                results["status"] = ReadinessStatus.DEGRADED
        else:
            results["checks"].append({"id": "stuck_runs", "name": "Stuck Agent Runs", "status": "pass", "value": 0})

        # 5. Orphan Leases and DLQ
        res_orphans = await self.db.execute(select(func.count(AgentExecutionLease.id)).where(AgentExecutionLease.expires_at <= utc_now()))
        orphan_leases = res_orphans.scalar() or 0
        results["checks"].append({
            "id": "orphan_leases",
            "name": "Orphan Execution Leases",
            "status": "pass" if orphan_leases == 0 else "warn",
            "value": orphan_leases
        })

        res_dlq = await self.db.execute(select(func.count(AgentExecutionDeadLetter.id)))
        dlq_count = res_dlq.scalar() or 0
        if dlq_count > 0:
            results["checks"].append({
                "id": "dead_letter_queue",
                "name": "Dead Letter Queue (DLQ)",
                "status": "fail",
                "value": dlq_count,
                "message": f"DLQ has {dlq_count} failed jobs."
            })
            results["warnings"].append(f"DLQ contains {dlq_count} items. Investigation required.")
            if results["status"] == ReadinessStatus.READY:
                results["status"] = ReadinessStatus.DEGRADED
        else:
            results["checks"].append({"id": "dead_letter_queue", "name": "Dead Letter Queue (DLQ)", "status": "pass", "value": 0})

        # 6. Policy and Memory Health
        res_mem_policies = await self.db.execute(select(func.count(AgentMemoryPolicy.id)))
        mem_policies = res_mem_policies.scalar() or 0
        results["checks"].append({
            "id": "memory_policies",
            "name": "Memory Policies Configured",
            "status": "pass" if mem_policies > 0 else "warn",
            "value": mem_policies
        })

        # 7. Approvals and Incidents
        res_approvals = await self.db.execute(select(func.count(AgentApprovalRequest.id)).where(AgentApprovalRequest.status == "pending"))
        pending_approvals = res_approvals.scalar() or 0
        results["checks"].append({
            "id": "approval_backlog",
            "name": "Pending Approvals",
            "status": "pass" if pending_approvals < 10 else "warn",
            "value": pending_approvals
        })

        res_incidents = await self.db.execute(select(func.count(AgentIncident.id)).where(AgentIncident.status == "open"))
        open_incidents = res_incidents.scalar() or 0
        results["checks"].append({
            "id": "incident_backlog",
            "name": "Open Incidents",
            "status": "pass" if open_incidents < 5 else "warn",
            "value": open_incidents
        })

        # Final Status Refinement
        if results["blockers"] and results["status"] not in [ReadinessStatus.DISABLED, ReadinessStatus.BLOCKED]:
            results["status"] = ReadinessStatus.BLOCKED
        elif results["warnings"] and results["status"] == ReadinessStatus.READY:
            results["status"] = ReadinessStatus.DEGRADED

        return results
