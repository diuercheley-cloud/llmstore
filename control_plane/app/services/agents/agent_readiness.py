"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentRun, AgentIncident
from app.models.agent_execution import AgentWorkerHeartbeat, AgentExecutionJob, AgentExecutionLease
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AgentReadinessService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def check_readiness(self) -> Dict[str, Any]:
        results = {
            "status": "ready",
            "timestamp": utc_now().isoformat(),
            "checks": {}
        }

        # 1. Runtime Enabled
        runtime_enabled = self.settings.agent_runtime_enabled
        results["checks"]["runtime_enabled"] = {
            "status": "pass" if runtime_enabled else "fail",
            "value": runtime_enabled
        }

        # 2. Worker Heartbeats
        res_workers = await self.db.execute(
            select(func.count(AgentWorkerHeartbeat.id))
            .where(AgentWorkerHeartbeat.last_heartbeat >= utc_now() - timedelta(minutes=5))
        )
        active_workers = res_workers.scalar() or 0
        results["checks"]["active_workers"] = {
            "status": "pass" if active_workers > 0 else "warn",
            "value": active_workers
        }

        # 3. Queue Depth
        res_queue = await self.db.execute(
            select(func.count(AgentExecutionJob.id))
            .where(AgentExecutionJob.status == "queued")
        )
        queue_depth = res_queue.scalar() or 0
        results["checks"]["queue_depth"] = {
            "status": "pass" if queue_depth < 100 else "warn",
            "value": queue_depth
        }

        # 4. Stuck Runs
        res_stuck = await self.db.execute(
            select(func.count(AgentRun.id))
            .where(AgentRun.status == "running")
            .where(AgentRun.created_at <= utc_now() - timedelta(hours=1))
        )
        stuck_runs = res_stuck.scalar() or 0
        results["checks"]["stuck_runs"] = {
            "status": "pass" if stuck_runs == 0 else "warn",
            "value": stuck_runs
        }

        # 5. Orphan Leases
        res_orphans = await self.db.execute(
            select(func.count(AgentExecutionLease.id))
            .where(AgentExecutionLease.expires_at <= utc_now())
        )
        orphan_leases = res_orphans.scalar() or 0
        results["checks"]["orphan_leases"] = {
            "status": "pass" if orphan_leases < 10 else "warn",
            "value": orphan_leases
        }

        # 6. Incident Backlog
        res_incidents = await self.db.execute(
            select(func.count(AgentIncident.id))
            .where(AgentIncident.status == "open")
            .where(AgentIncident.severity == "critical")
        )
        critical_incidents = res_incidents.scalar() or 0
        results["checks"]["critical_incidents"] = {
            "status": "pass" if critical_incidents == 0 else "fail",
            "value": critical_incidents
        }

        # Determine overall status
        for check in results["checks"].values():
            if check["status"] == "fail":
                results["status"] = "unhealthy"
                break
            if check["status"] == "warn" and results["status"] == "ready":
                results["status"] = "degraded"

        return results
