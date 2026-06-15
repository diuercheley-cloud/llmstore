"""
Owner: platform-ops
Status: implementation
"""

import enum
import logging
import os
from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_execution import AgentWorkerHeartbeat
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ReadinessStatus(enum.Enum):
    DISABLED = "disabled"
    DEV_READY = "dev_ready"
    PILOT_READY = "pilot_ready"
    PRODUCTION_BLOCKED = "production_blocked"
    PRODUCTION_READY = "production_ready"


class RealExecutionReadinessService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._base_dir = Path(__file__).resolve().parents[4]

    async def check_readiness(self) -> dict[str, Any]:
        deployment_mode = getattr(self.settings, "deployment_mode", "appliance")
        production_like = deployment_mode in ("production", "enterprise_managed")
        pilot_like = deployment_mode == "pilot"

        results = {
            "status": ReadinessStatus.PRODUCTION_READY.value,
            "checks": [],
            "blockers": [],
            "warnings": [],
            "timestamp": utc_now().isoformat(),
        }

        def add_check(
            check_id: str, name: str, status: str, value: Any, message: str | None = None
        ) -> None:
            payload = {"id": check_id, "name": name, "status": status, "value": value}
            if message:
                payload["message"] = message
            results["checks"].append(payload)

        exec_enabled = bool(self.settings.agent_execution_enabled)
        mock_mode = bool(getattr(self.settings, "agent_executor_mock_mode", False))
        dry_run_mode = bool(getattr(self.settings, "agent_executor_dry_run_mode", False))
        simulation_mode = bool(getattr(self.settings, "agent_executor_allow_simulation", False))
        active_modes = [
            mode
            for mode, enabled in (
                ("mock", mock_mode),
                ("dry_run", dry_run_mode),
                ("simulation", simulation_mode),
            )
            if enabled
        ]

        exec_status = "pass"
        exec_message = "AgentExecutor is configured for real execution."
        if mock_mode or dry_run_mode:
            exec_status = "fail" if (production_like or pilot_like) else "warn"
            exec_message = f"Non-real executor modes enabled: {', '.join(active_modes)}."
            if production_like or pilot_like:
                results["blockers"].append(f"Mock execution mode is enabled in {deployment_mode}.")
            else:
                results["warnings"].append(exec_message)
        elif not exec_enabled:
            exec_status = "fail" if production_like else "warn"
            exec_message = "Real tool execution is disabled."
            if production_like:
                results["blockers"].append(
                    "Real tool execution is disabled in production-like mode."
                )
            elif pilot_like:
                results["warnings"].append(
                    "Real tool execution is disabled; pilot will not exercise real side effects."
                )
            else:
                results["warnings"].append("Real tool execution is disabled.")
        add_check(
            "execution_mode",
            "Real Execution Mode",
            exec_status,
            {"execution_enabled": exec_enabled, "active_modes": active_modes},
            exec_message,
        )

        queue_enabled = bool(
            getattr(
                self.settings,
                "agent_execution_plane_enabled",
                self.settings.agent_execution_enabled,
            )
        )
        queue_status = "pass" if queue_enabled else "fail"
        queue_message = (
            "Durable execution queue is enabled."
            if queue_enabled
            else "Durable execution queue is disabled."
        )
        if not queue_enabled and (production_like or pilot_like):
            results["blockers"].append(
                "Durable execution queue is disabled but required for production/pilot."
            )
        add_check(
            "durable_queue", "Durable Queue Status", queue_status, queue_enabled, queue_message
        )

        scheduler_enabled = bool(getattr(self.settings, "agent_cron_triggers_enabled", False))
        scheduler_status = "pass"
        scheduler_message = "Scheduler safety prerequisites satisfied."
        if scheduler_enabled and not queue_enabled:
            scheduler_status = "fail" if (production_like or pilot_like) else "warn"
            scheduler_message = "Scheduler requires the durable queue to be enabled."
            if production_like or pilot_like:
                results["blockers"].append("Scheduler is enabled without a durable queue.")
            else:
                results["warnings"].append(scheduler_message)
        add_check(
            "scheduler_safety",
            "Scheduler Safety",
            scheduler_status,
            {"cron_enabled": scheduler_enabled, "queue_enabled": queue_enabled},
            scheduler_message,
        )

        active_workers = 0
        worker_status = "pass"
        worker_message = "Worker heartbeat check skipped because workers are disabled."
        try:
            res_workers = await self.db.execute(
                select(func.count(AgentWorkerHeartbeat.worker_id))
                .where(AgentWorkerHeartbeat.last_heartbeat >= utc_now() - timedelta(minutes=5))
                .where(AgentWorkerHeartbeat.status == "active")
            )
            active_workers = res_workers.scalar() or 0
            worker_status = (
                "pass" if active_workers > 0 or not self.settings.agent_worker_enabled else "warn"
            )
            worker_message = f"{active_workers} active workers observed in the last 5 minutes."
            if (
                active_workers == 0
                and self.settings.agent_worker_enabled
                and (production_like or pilot_like)
            ):
                worker_status = "fail"
                results["blockers"].append(
                    "No active worker heartbeats detected in the last 5 minutes."
                )
            elif active_workers == 0 and self.settings.agent_worker_enabled:
                results["warnings"].append("No active workers detected.")
        except Exception as exc:
            worker_status = "warn"
            worker_message = f"Worker heartbeat check unavailable: {exc.__class__.__name__}"
            if production_like or pilot_like:
                worker_status = "fail"
                results["blockers"].append("Worker heartbeat store is unreachable.")
            else:
                results["warnings"].append(
                    "Worker heartbeat store is unreachable in non-production mode."
                )
        add_check(
            "active_workers",
            "Active Worker Presence",
            worker_status,
            active_workers,
            worker_message,
        )

        sandbox_enabled = bool(getattr(self.settings, "agent_tool_sandbox_enabled", False))
        sandbox_status = "pass" if sandbox_enabled else "warn"
        sandbox_message = "Tool sandbox is enabled."
        if not sandbox_enabled:
            sandbox_message = "Tool sandbox is disabled."
            if production_like:
                sandbox_status = "fail"
                results["blockers"].append(
                    "Sandbox execution is disabled in production environment."
                )
            elif pilot_like:
                results["warnings"].append("Sandbox execution is disabled.")
        add_check(
            "sandbox_hardened",
            "Sandbox Hardening",
            sandbox_status,
            sandbox_enabled,
            sandbox_message,
        )

        connector_mode = str(getattr(self.settings, "agent_connector_mode", "mock")).strip().lower()
        connector_real_http = bool(
            getattr(self.settings, "agent_connector_real_http_enabled", False)
        )
        connector_status = "pass"
        connector_message = f"Connectors use explicit mode '{connector_mode}'."
        if connector_mode not in {"mock", "real"}:
            connector_status = "fail"
            results["blockers"].append(f"Unsupported AGENT_CONNECTOR_MODE '{connector_mode}'.")
            connector_message = "AGENT_CONNECTOR_MODE must be 'mock' or 'real'."
        elif connector_mode == "real" and not connector_real_http:
            connector_status = "fail" if (production_like or pilot_like) else "warn"
            connector_message = "Connector mode is real but outbound real HTTP is disabled."
            if production_like or pilot_like:
                results["blockers"].append(
                    "Connector mode is real while AGENT_CONNECTOR_REAL_HTTP_ENABLED=false."
                )
            else:
                results["warnings"].append(connector_message)
        add_check(
            "connectors_mode",
            "Connectors Explicit Mode",
            connector_status,
            {"mode": connector_mode, "real_http_enabled": connector_real_http},
            connector_message,
        )

        operator_mode = (
            str(
                os.environ.get(
                    "OPERATOR_MODE",
                    "real" if not self._env_truthy("OPERATOR_DRY_RUN") else "dry_run",
                )
            )
            .strip()
            .lower()
        )
        operator_status = "pass"
        operator_message = f"Operator mode is '{operator_mode}'."
        if production_like and operator_mode != "real":
            operator_status = "fail"
            results["blockers"].append(
                f"Kubernetes operator mode '{operator_mode}' does not allow real reconciliation."
            )
        elif pilot_like and operator_mode not in {"real", "mock"}:
            operator_status = "warn"
            results["warnings"].append(operator_message)
        add_check(
            "k8s_operator",
            "Kubernetes Operator Type",
            operator_status,
            operator_mode,
            operator_message,
        )

        code_findings = self._scan_code_integrity()
        code_status = "pass" if not code_findings else "fail"
        if code_findings:
            results["blockers"].extend(code_findings)
        add_check(
            "code_integrity",
            "Execution Logic Integrity",
            code_status,
            "No placeholder fallbacks in execution hot paths"
            if not code_findings
            else code_findings,
            "Execution hot paths have no implicit mock or NotImplementedError fallback."
            if not code_findings
            else "; ".join(code_findings),
        )

        if results["blockers"]:
            results["status"] = ReadinessStatus.PRODUCTION_BLOCKED.value
        elif production_like:
            results["status"] = ReadinessStatus.PRODUCTION_READY.value
        elif pilot_like:
            results["status"] = ReadinessStatus.PILOT_READY.value
        elif not exec_enabled:
            results["status"] = ReadinessStatus.DEV_READY.value
        else:
            results["status"] = ReadinessStatus.PRODUCTION_READY.value

        return results

    def _env_truthy(self, name: str) -> bool:
        return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}

    def _scan_code_integrity(self) -> list[str]:
        findings: list[str] = []
        for relative_path, blocked_patterns in self._code_scan_rules().items():
            file_path = self._base_dir / relative_path
            try:
                content = file_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                findings.append(f"Required execution file missing: {relative_path}")
                continue

            for pattern in blocked_patterns:
                if pattern in content:
                    findings.append(f"{relative_path} still contains blocked pattern: {pattern}")
        return findings

    def _code_scan_rules(self) -> dict[str, Iterable[str]]:
        return {
            "control_plane/app/services/agents/tool_executor.py": [
                "Simulated execution of tool",
            ],
            "control_plane/app/services/agents/connectors/github_connector.py": [
                "NotImplementedError"
            ],
            "control_plane/app/services/agents/connectors/confluence_connector.py": [
                "NotImplementedError"
            ],
            "control_plane/app/services/agents/connectors/jira_connector.py": [
                "NotImplementedError"
            ],
            "control_plane/app/services/agents/connectors/slack_connector.py": [
                "NotImplementedError"
            ],
            "control_plane/app/services/agents/connectors/microsoft365_connector.py": [
                "NotImplementedError"
            ],
            "control_plane/app/services/agents/connectors/salesforce_connector.py": [
                "NotImplementedError"
            ],
        }
