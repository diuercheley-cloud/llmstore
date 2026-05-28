# Owner: agent-platform
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
from app.services.agents.agent_llm_provider import LLMProviderType

logger = logging.getLogger(__name__)

VALID_LLM_PROVIDERS = {e.value for e in LLMProviderType}

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
                "message": "Agentic runtime is disabled by configuration (opt-out)."
            })
            return results

        results["checks"].append({
            "id": "runtime_enabled",
            "name": "Agent Runtime Enabled",
            "status": "pass",
            "value": True
        })

        # 1b. LLM Provider Mode Check
        llm_provider = getattr(self.settings, "agent_llm_provider", "mock")
        deployment_mode = getattr(self.settings, "deployment_mode", "appliance")
        allow_mock_in_prod = getattr(self.settings, "agent_allow_mock_llm_in_production", False)
        require_real = getattr(self.settings, "agent_require_real_llm_for_production", True)
        executor_mock_mode = bool(getattr(self.settings, "agent_executor_mock_mode", False))
        executor_dry_run_mode = bool(getattr(self.settings, "agent_executor_dry_run_mode", False))
        executor_simulation_mode = bool(getattr(self.settings, "agent_executor_allow_simulation", False))

        if llm_provider not in VALID_LLM_PROVIDERS:
            results["checks"].append({
                "id": "llm_provider",
                "name": "LLM Provider Valid",
                "status": "fail",
                "value": llm_provider,
                "message": f"Invalid LLM provider '{llm_provider}'. Must be one of: {sorted(VALID_LLM_PROVIDERS)}"
            })
            results["blockers"].append(f"Invalid LLM provider configured: {llm_provider}")
            results["status"] = ReadinessStatus.BLOCKED
        else:
            provider_status = "pass"
            messages = []

            if llm_provider == "mock" and deployment_mode in ("production", "enterprise_managed"):
                if allow_mock_in_prod:
                    provider_status = "warn"
                    messages.append(
                        f"Mock LLM provider active in '{deployment_mode}' mode with override. "
                        "Use gateway or real provider for GA workloads."
                    )
                    results["warnings"].extend(messages)
                    if results["status"] == ReadinessStatus.READY:
                        results["status"] = ReadinessStatus.DEGRADED
                else:
                    provider_status = "fail"
                    messages.append(
                        f"Mock LLM provider blocked in '{deployment_mode}' mode. "
                        "Set AGENT_LLM_PROVIDER=gateway or AGENT_LLM_PROVIDER=real."
                    )
                    results["blockers"].extend(messages)
                    results["status"] = ReadinessStatus.BLOCKED

            elif llm_provider == "mock" and deployment_mode == "pilot":
                provider_status = "warn"
                messages.append(
                    "Mock LLM provider used in pilot mode. "
                    "Use gateway or real provider for meaningful pilot evaluation."
                )
                results["warnings"].extend(messages)
                if results["status"] == ReadinessStatus.READY:
                    results["status"] = ReadinessStatus.DEGRADED

            elif llm_provider in ("gateway", "real") and deployment_mode in ("production", "enterprise_managed"):
                if not require_real:
                    provider_status = "warn"
                    messages.append(
                        "AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION is disabled. "
                        "Production readiness posture is weakened."
                    )
                    results["warnings"].extend(messages)
                    if results["status"] == ReadinessStatus.READY:
                        results["status"] = ReadinessStatus.DEGRADED

            results["checks"].append({
                "id": "llm_provider",
                "name": "LLM Provider Status",
                "status": provider_status,
                "value": {"provider": llm_provider, "mode": deployment_mode},
                "message": "; ".join(messages) if messages else f"LLM provider '{llm_provider}' is valid for '{deployment_mode}' mode."
            })

        # 1c. Executor Mock/Simulation Posture
        executor_modes = []
        if executor_mock_mode:
            executor_modes.append("mock")
        if executor_dry_run_mode:
            executor_modes.append("dry_run")
        if executor_simulation_mode:
            executor_modes.append("simulation")

        if not executor_modes:
            results["checks"].append({
                "id": "executor_modes",
                "name": "Agent Executor Execution Mode",
                "status": "pass",
                "value": {"active_modes": [], "mode": deployment_mode},
                "message": "AgentExecutor is configured for real execution only."
            })
        else:
            message = (
                f"AgentExecutor non-real modes active: {', '.join(executor_modes)}. "
                "All simulated outputs must remain audit-visible."
            )
            check_status = "warn"
            if deployment_mode in ("pilot", "production", "enterprise_managed"):
                check_status = "fail"
                results["blockers"].append(message)
                if results["status"] != ReadinessStatus.DISABLED:
                    results["status"] = ReadinessStatus.BLOCKED
            else:
                results["warnings"].append(message)
                if results["status"] == ReadinessStatus.READY:
                    results["status"] = ReadinessStatus.DEGRADED

            results["checks"].append({
                "id": "executor_modes",
                "name": "Agent Executor Execution Mode",
                "status": check_status,
                "value": {"active_modes": executor_modes, "mode": deployment_mode},
                "message": message
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
        res_queue = await self.db.execute(select(func.count(AgentExecutionJob.id)).where(AgentExecutionJob.queue_status == "queued"))
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
