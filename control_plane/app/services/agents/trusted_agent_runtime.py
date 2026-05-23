# Owner: agent-platform
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentExecution,
    CommercialAgentMemoryBoundary,
    CommercialAgentProfile,
    CommercialToolApproval,
    CommercialToolRegistry,
)
from app.services.agents.execution_receipts import (
    build_action_receipt,
    canonical_json,
    redact_confidential_payload,
    sha256_hex,
)
from app.services.agents.tool_policy_engine import PolicyDecision, ToolPolicyEngine
from app.services.billing.financial_audit_trail import FinancialAuditTrailService
from app.services.inference.confidential_runtime import log_confidential_audit

ToolHandler = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass
class SandboxedExecutionContext:
    mode: str = "internal"
    shell_enabled: bool = False
    network_access: str = "offline"
    filesystem_scope: str = "tenant-scoped"

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "shell_enabled": self.shell_enabled,
            "network_access": self.network_access,
            "filesystem_scope": self.filesystem_scope,
        }


class TrustedAgentRuntime:
    def __init__(self) -> None:
        self.policy_engine = ToolPolicyEngine()
        self._handlers: dict[str, ToolHandler] = {}

    def register_tool_handler(self, tool_name: str, handler: ToolHandler) -> None:
        self._handlers[tool_name] = handler

    def build_deterministic_plan(self, actions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, str]:
        normalized: list[dict[str, Any]] = []
        previous_node_hash: str | None = None
        for index, action in enumerate(actions):
            normalized_action = {
                "action_index": index,
                "action_name": action.get("action_name") or action["tool_name"],
                "tool_name": action["tool_name"],
                "payload": action.get("payload", {}),
                "requires_approval": bool(action.get("requires_approval", False)),
            }
            normalized_action["planned_input_hash"] = sha256_hex(canonical_json(normalized_action["payload"]))
            normalized_action["graph_node_hash"] = sha256_hex(
                canonical_json(
                    {
                        "index": index,
                        "tool_name": normalized_action["tool_name"],
                        "planned_input_hash": normalized_action["planned_input_hash"],
                        "previous_node_hash": previous_node_hash,
                    }
                )
            )
            previous_node_hash = normalized_action["graph_node_hash"]
            normalized.append(normalized_action)
        replay_safe_plan = [
            {
                "action_index": row["action_index"],
                "action_name": row["action_name"],
                "tool_name": row["tool_name"],
                "requires_approval": row["requires_approval"],
                "planned_input_hash": row["planned_input_hash"],
                "graph_node_hash": row["graph_node_hash"],
            }
            for row in normalized
        ]
        plan_hash = sha256_hex(canonical_json(replay_safe_plan))
        graph_hash = sha256_hex(canonical_json([row["graph_node_hash"] for row in normalized]))
        return normalized, plan_hash, graph_hash

    async def create_execution(
        self,
        db: AsyncSession,
        *,
        agent_id: UUID,
        tenant_id: str,
        session_id: str,
        input_payload: dict[str, Any],
        action_plan: list[dict[str, Any]],
        runtime_mode: str = "enforce",
        dry_run: bool = False,
    ) -> CommercialAgentExecution:
        profile = await db.get(CommercialAgentProfile, agent_id)
        if profile is None:
            raise ValueError("agent_not_found")
        if profile.client_id and profile.client_id != tenant_id:
            raise ValueError("tenant_scope_violation")
        normalized_plan, plan_hash, graph_hash = self.build_deterministic_plan(action_plan)
        runtime_snapshot_hash = sha256_hex(
            canonical_json(
                {
                    "tenant_id": tenant_id,
                    "memory_isolation_mode": profile.memory_isolation_mode,
                    "confidential_runtime_required": profile.confidential_runtime_required,
                    "runtime_mode": runtime_mode,
                    "dry_run": dry_run,
                }
            )
        )
        execution = CommercialAgentExecution(
            agent_id=agent_id,
            tenant_id=tenant_id,
            session_id=session_id,
            status="running",
            input_hash=sha256_hex(canonical_json(input_payload)),
            plan_hash=plan_hash,
            execution_graph_hash=graph_hash,
            runtime_snapshot_hash=runtime_snapshot_hash,
            runtime_mode=runtime_mode,
            dry_run=dry_run,
            confidential_payload_mode="redacted" if profile.confidential_runtime_required else "allow",
            metadata_json={
                "plan": [
                    {k: v for k, v in action.items() if k != "payload"}
                    | {"payload": redact_confidential_payload(action["payload"])}
                    for action in normalized_plan
                ],
                "input_payload": redact_confidential_payload(input_payload),
                "tenant_id": tenant_id,
                "sovereign_appliance_mode": True,
            },
        )
        db.add(execution)
        await db.flush()

        boundary = CommercialAgentMemoryBoundary(
            execution_id=execution.id,
            tenant_id=tenant_id,
            boundary_type=profile.memory_isolation_mode,
            access_log_hash=sha256_hex(f"{execution.id}:{tenant_id}:{profile.memory_isolation_mode}"),
        )
        db.add(boundary)
        await db.flush()

        previous_action_hash = None
        for action in normalized_plan:
            row = CommercialAgentAction(
                execution_id=execution.id,
                tenant_id=tenant_id,
                action_index=action["action_index"],
                action_name=action["action_name"],
                tool_name=action["tool_name"],
                status="planned",
                planned_input_hash=action["planned_input_hash"],
                previous_action_hash=previous_action_hash,
                graph_node_hash=action["graph_node_hash"],
                confidential_mode=execution.confidential_payload_mode,
                metadata_json={"payload": redact_confidential_payload(action["payload"])},
            )
            db.add(row)
            previous_action_hash = action["graph_node_hash"]

        if profile.confidential_runtime_required:
            await log_confidential_audit(
                db,
                session_id=None,
                event_type="trusted_agent_execution_created",
                summary=f"Trusted runtime execution {execution.id} created for tenant {tenant_id}",
            )

        return execution

    async def execute_plan(self, db: AsyncSession, *, execution_id: UUID) -> CommercialAgentExecution:
        execution = await db.get(CommercialAgentExecution, execution_id)
        if execution is None:
            raise ValueError("execution_not_found")
        profile = await db.get(CommercialAgentProfile, execution.agent_id)
        if profile is None:
            raise ValueError("agent_not_found")

        action_rows = (
            await db.execute(
                select(CommercialAgentAction)
                .where(CommercialAgentAction.execution_id == execution_id)
                .order_by(CommercialAgentAction.action_index.asc())
            )
        ).scalars().all()

        previous_receipt_hash = None
        for action in action_rows:
            payload = ((action.metadata_json or {}).get("payload")) or {}
            decision = await self.policy_engine.evaluate_action(
                db,
                profile=profile,
                execution=execution,
                tool_name=action.tool_name,
                payload=payload,
                dry_run=execution.dry_run,
            )
            await self._apply_policy_decision(db, execution=execution, action=action, decision=decision)
            if not decision.allowed:
                execution.status = "blocked"
                execution.policy_decision = "denied"
                continue
            if decision.requires_approval:
                execution.approval_required = True
                execution.approval_status = "pending"
                execution.policy_decision = "pending_approval"
                action.status = "pending_approval"
                continue

            result_hash = None
            action.status = "executed" if not execution.dry_run else "dry_run"
            if not execution.dry_run:
                handler = self._handlers.get(action.tool_name)
                if handler is None:
                    action.status = "denied"
                    action.policy_decision_json = {"decision": "denied", "reason": "missing_runtime_handler"}
                    execution.status = "blocked"
                    execution.policy_decision = "denied"
                    continue
                runtime_context = {
                    "tenant_id": execution.tenant_id,
                    "execution_id": str(execution.id),
                    "sandbox": SandboxedExecutionContext(
                        mode=(decision.tool.execution_mode if decision.tool else "internal")
                    ).as_dict(),
                }
                handler_result = handler(payload, runtime_context)
                if inspect.isawaitable(handler_result):
                    handler_result = await handler_result
                result_hash = sha256_hex(canonical_json(redact_confidential_payload(handler_result)))
                action.result_hash = result_hash
            else:
                result_hash = sha256_hex("dry_run")
                action.result_hash = result_hash

            receipt = build_action_receipt(
                execution_id=str(execution.id),
                tenant_id=execution.tenant_id or "",
                action_index=action.action_index,
                tool_name=action.tool_name,
                planned_input_hash=action.planned_input_hash,
                result_hash=result_hash,
                policy_decision=decision.decision,
                runtime_snapshot_hash=execution.runtime_snapshot_hash,
                previous_action_hash=previous_receipt_hash,
                execution_graph_hash=execution.execution_graph_hash,
                sandbox_context=action.sandbox_context_json,
            )
            action.receipt_hash = receipt["receipt_hash"]
            action.detached_signature = receipt["detached_signature"]
            action.signature_algorithm = receipt["signature_algorithm"]
            action.action_hash = sha256_hex(
                canonical_json(
                    {
                        "receipt_hash": action.receipt_hash,
                        "result_hash": action.result_hash,
                        "planned_input_hash": action.planned_input_hash,
                    }
                )
            )
            metadata = action.metadata_json or {}
            metadata["immutable_hash"] = receipt["immutable_hash"]
            metadata["runtime_snapshot_hash"] = execution.runtime_snapshot_hash
            action.metadata_json = metadata
            previous_receipt_hash = action.receipt_hash

            await FinancialAuditTrailService.create_audit_event(
                db,
                event_type="trusted_agent_action_executed",
                related_record_type="commercial_agent_action",
                related_record_id=str(action.id),
                metadata_json={
                    "tenant_id": execution.tenant_id,
                    "tool_name": action.tool_name,
                    "receipt_hash": action.receipt_hash,
                    "replay_status": execution.replay_status,
                },
            )

        execution.output_hash = sha256_hex(
            canonical_json(
                [
                    {"action_index": row.action_index, "result_hash": row.result_hash, "status": row.status}
                    for row in action_rows
                ]
            )
        )
        execution.audit_chain_hash = sha256_hex(
            canonical_json([row.receipt_hash for row in action_rows if row.receipt_hash])
        )
        if execution.status == "running":
            execution.status = "completed"
            execution.policy_decision = execution.policy_decision or "allowed"
            execution.approval_status = execution.approval_status or "not_required"
        execution.completed_at = utc_now()
        return execution

    async def approve_action(
        self,
        db: AsyncSession,
        *,
        action_id: UUID,
        approved_by: str,
        status: str,
        decision_reason: str | None = None,
    ) -> CommercialToolApproval:
        action = await db.get(CommercialAgentAction, action_id)
        if action is None:
            raise ValueError("action_not_found")
        execution = await db.get(CommercialAgentExecution, action.execution_id)
        if execution is None:
            raise ValueError("execution_not_found")

        approval = (
            await db.execute(
                select(CommercialToolApproval).where(CommercialToolApproval.action_id == action_id)
            )
        ).scalars().first()
        if approval is None:
            approval = CommercialToolApproval(
                action_id=action.id,
                execution_id=execution.id,
                tenant_id=action.tenant_id,
                requested_by="system",
                status="pending",
                approval_chain_hash=sha256_hex(f"{action.id}:{action.tool_name}:{action.tenant_id}"),
            )
            db.add(approval)
        approval.status = status
        approval.approved_by = approved_by
        approval.decision_reason = decision_reason
        approval.decided_at = utc_now()
        action.approval_status = status
        action.status = "approved" if status == "approved" else "denied"
        execution.approval_status = status
        if status == "rejected":
            execution.status = "blocked"
            execution.policy_decision = "denied"
        return approval

    async def summarize_runtime(self, db: AsyncSession) -> dict[str, Any]:
        total_executions = await db.scalar(select(func.count(CommercialAgentExecution.id)))
        total_actions = await db.scalar(select(func.count(CommercialAgentAction.id)))
        total_tools = await db.scalar(select(func.count(CommercialToolRegistry.id)))
        pending_approvals = await db.scalar(
            select(func.count(CommercialToolApproval.id)).where(CommercialToolApproval.status == "pending")
        )
        violations = await db.scalar(
            select(func.count(CommercialAgentAction.id)).where(CommercialAgentAction.status == "denied")
        )
        verified_replays = await db.scalar(
            select(func.count(CommercialAgentExecution.id)).where(CommercialAgentExecution.replay_status == "verified")
        )
        return {
            "enabled": True,
            "mode": "trusted",
            "total_executions": total_executions or 0,
            "total_actions": total_actions or 0,
            "registered_tools": total_tools or 0,
            "pending_approvals": pending_approvals or 0,
            "policy_violations": violations or 0,
            "verified_replays": verified_replays or 0,
        }

    async def _apply_policy_decision(
        self,
        db: AsyncSession,
        *,
        execution: CommercialAgentExecution,
        action: CommercialAgentAction,
        decision: PolicyDecision,
    ) -> None:
        action.policy_decision_json = {
            "decision": decision.decision,
            "reason": decision.reason,
            "payload_hash": decision.payload_hash,
        }
        action.sandbox_context_json = SandboxedExecutionContext(
            mode=(decision.tool.execution_mode if decision.tool else "internal")
        ).as_dict()
        action.approval_status = "pending" if decision.requires_approval else "not_required"
        action.metadata_json = {
            **(action.metadata_json or {}),
            "payload": decision.sanitized_payload,
            "tool_provenance_hash": decision.tool.provenance_hash if decision.tool else None,
        }
        if not decision.allowed:
            action.status = "denied"
            return
        if decision.requires_approval:
            approval = CommercialToolApproval(
                action_id=action.id,
                execution_id=execution.id,
                tenant_id=action.tenant_id,
                requested_by="system",
                status="pending",
                approval_chain_hash=sha256_hex(f"{action.id}:{execution.id}:{action.tool_name}"),
                metadata_json={"reason": decision.reason},
            )
            db.add(approval)


trusted_agent_runtime = TrustedAgentRuntime()
trusted_agent_runtime.register_tool_handler(
    "echo",
    lambda payload, runtime_context: {
        "echo": payload,
        "tenant_id": runtime_context["tenant_id"],
        "sandbox": runtime_context["sandbox"]["mode"],
    },
)
