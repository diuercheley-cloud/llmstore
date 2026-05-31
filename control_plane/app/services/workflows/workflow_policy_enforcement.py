from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowPolicyBinding,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowStage,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService, sign_governance_payload
from app.services.workflows.workflow_provenance import redact_sensitive_payload, sha256_hex


class WorkflowPolicyEnforcementService:
    def __init__(self) -> None:
        self.ledger = WorkflowGovernanceLedgerService()

    async def _resolve_policy_bundle(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None,
        bundle_ref: str | None,
    ) -> CommercialPolicyBundle | None:
        if not bundle_ref:
            return None
        stmt = select(CommercialPolicyBundle).where(CommercialPolicyBundle.status == "active")
        candidate: CommercialPolicyBundle | None = None
        try:
            bundle_uuid = uuid.UUID(str(bundle_ref))
        except (TypeError, ValueError):
            bundle_uuid = None
        if bundle_uuid:
            candidate = (await db.execute(stmt.where(CommercialPolicyBundle.id == bundle_uuid))).scalar_one_or_none()
        if candidate is None:
            candidate = (
                await db.execute(
                    stmt.where(
                        (CommercialPolicyBundle.immutable_hash == bundle_ref)
                        | (CommercialPolicyBundle.bundle_name == bundle_ref)
                    )
                    .order_by(desc(CommercialPolicyBundle.activated_at), desc(CommercialPolicyBundle.created_at))
                )
            ).scalars().first()
        if candidate is None:
            return None
        bundle_client_id = str(candidate.client_id) if candidate.client_id else None
        if bundle_client_id and tenant_id and bundle_client_id != tenant_id:
            return None
        return candidate

    def _stage_runtime_context(
        self,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
    ) -> dict[str, Any]:
        return sanitize_report_payload(
            {
                "tenant_id": execution.tenant_id,
                "request_id": execution.request_id,
                "execution_mode": execution.execution_mode,
                "stage_key": stage.stage_key,
                "stage_type": stage.stage_type,
                "policy_gate_status": stage.policy_gate_status,
                "runtime": ((stage.metadata_json or {}).get("runtime")) or {},
            }
        )

    async def bind_stage_policy(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
        actor_id: str = "system",
    ) -> tuple[CommercialWorkflowPolicyBinding, CommercialWorkflowPolicySnapshot | None]:
        stage_policy = sanitize_report_payload((((stage.metadata_json or {}).get("policy")) or {}))
        bundle_ref = stage_policy.get("bundle_ref") or stage.bound_policy_bundle_id or None
        bundle = await self._resolve_policy_bundle(db, tenant_id=execution.tenant_id, bundle_ref=str(bundle_ref) if bundle_ref else None)
        runtime_context = self._stage_runtime_context(execution, stage)
        runtime_policy_hash = sha256_hex({"policy": stage_policy, "runtime": runtime_context})
        policy_json = sanitize_report_payload(bundle.rules_json if bundle else stage_policy)
        snapshot_hash = sha256_hex({"policy": policy_json, "runtime": runtime_context, "stage_key": stage.stage_key})
        binding = CommercialWorkflowPolicyBinding(
            execution_id=execution.id,
            stage_id=stage.id,
            tenant_id=execution.tenant_id,
            bundle_id=bundle.id if bundle else None,
            bundle_ref=str(bundle_ref) if bundle_ref else None,
            binding_status="bound" if bundle else "missing",
            enforcement_mode=stage_policy.get("enforcement_mode") or (bundle.mode if bundle else "enforce"),
            runtime_policy_hash=runtime_policy_hash,
            snapshot_hash=snapshot_hash,
            immutable_hash=sha256_hex(
                {
                    "execution_id": str(execution.id),
                    "stage_id": str(stage.id),
                    "bundle_id": str(bundle.id) if bundle else None,
                    "runtime_policy_hash": runtime_policy_hash,
                    "snapshot_hash": snapshot_hash,
                }
            ),
            metadata_json={"stage_policy": stage_policy},
        )
        db.add(binding)
        await db.flush()
        snapshot = None
        if bundle is not None:
            snapshot = CommercialWorkflowPolicySnapshot(
                execution_id=execution.id,
                stage_id=stage.id,
                binding_id=binding.id,
                tenant_id=execution.tenant_id,
                snapshot_type="runtime",
                policy_hash=sha256_hex(policy_json),
                runtime_context_hash=sha256_hex(runtime_context),
                snapshot_hash=snapshot_hash,
                detached_signature=sign_governance_payload({"snapshot_hash": snapshot_hash}, scope="workflow_policy_snapshot"),
                signature_algorithm="ed25519",
                immutable_hash=sha256_hex({"snapshot_hash": snapshot_hash, "policy_hash": sha256_hex(policy_json)}),
                policy_json=policy_json,
                runtime_context_json=runtime_context,
                metadata_json={"bundle_name": bundle.bundle_name, "bundle_mode": bundle.mode},
            )
            db.add(snapshot)
            await db.flush()
            stage.bound_policy_bundle_id = bundle.id
            stage.active_policy_snapshot_id = snapshot.id
        await self.ledger.append_event(
            db,
            execution=execution,
            stage_id=stage.id,
            event_type="stage_policy_bound",
            actor_id=actor_id,
            actor_metadata={"bundle_ref": bundle_ref, "binding_status": binding.binding_status},
            event_summary=f"Policy binding recorded for stage {stage.stage_key}",
            event_payload={
                "stage_key": stage.stage_key,
                "binding_id": str(binding.id),
                "snapshot_id": str(snapshot.id) if snapshot else None,
                "binding_status": binding.binding_status,
                "enforcement_mode": binding.enforcement_mode,
            },
        )
        await db.flush()
        return binding, snapshot

    async def ensure_stage_binding(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
    ) -> tuple[CommercialWorkflowPolicyBinding, CommercialWorkflowPolicySnapshot | None]:
        existing = (
            await db.execute(
                select(CommercialWorkflowPolicyBinding)
                .where(
                    CommercialWorkflowPolicyBinding.execution_id == execution.id,
                    CommercialWorkflowPolicyBinding.stage_id == stage.id,
                )
                .order_by(desc(CommercialWorkflowPolicyBinding.created_at), desc(CommercialWorkflowPolicyBinding.id))
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            snapshot = None
            if stage.active_policy_snapshot_id:
                snapshot = await db.get(CommercialWorkflowPolicySnapshot, stage.active_policy_snapshot_id)
            return existing, snapshot
        return await self.bind_stage_policy(db, execution=execution, stage=stage)

    async def evaluate_stage(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
    ) -> dict[str, Any]:
        binding, snapshot = await self.ensure_stage_binding(db, execution=execution, stage=stage)
        stage_policy = (((stage.metadata_json or {}).get("policy")) or {})
        if snapshot is None or binding.binding_status != "bound":
            stage.policy_gate_status = "denied"
            stage.governance_mode = binding.enforcement_mode
            stage.drift_status = "missing_policy"
            return {
                "decision": "deny",
                "reason": "missing_valid_policy",
                "approval_required": False,
                "enforcement_mode": binding.enforcement_mode,
                "snapshot_id": None,
            }
        expected_runtime_hash = snapshot.runtime_context_hash
        actual_runtime_hash = sha256_hex(self._stage_runtime_context(execution, stage))
        drift_detected = expected_runtime_hash != actual_runtime_hash
        stage.drift_status = "drift_detected" if drift_detected else "aligned"
        mode = binding.enforcement_mode
        approval_required = bool(stage_policy.get("approval_required") or snapshot.policy_json.get("approval_required"))
        if drift_detected:
            execution.drift_detected = True
            await self.ledger.append_event(
                db,
                execution=execution,
                stage_id=stage.id,
                event_type="drift_detected",
                actor_id="system",
                actor_metadata={"stage_key": stage.stage_key},
                event_summary=f"Policy drift detected on stage {stage.stage_key}",
                event_payload={
                    "stage_key": stage.stage_key,
                    "expected_runtime_hash": expected_runtime_hash,
                    "observed_runtime_hash": actual_runtime_hash,
                },
            )
        if mode == "dry_run":
            decision = "allow"
            reason = "dry_run"
            stage.policy_gate_status = "report_only"
        elif mode == "report_only":
            decision = "allow"
            reason = "report_only"
            stage.policy_gate_status = "report_only"
        else:
            denied = bool(snapshot.policy_json.get("deny_execution") or stage_policy.get("deny_execution"))
            decision = "deny" if denied else "allow"
            reason = "policy_denied" if denied else "enforced"
            stage.policy_gate_status = "denied" if denied else "allowed"
        stage.approval_required = approval_required
        stage.governance_mode = mode
        signed_payload = {
            "stage_key": stage.stage_key,
            "decision": decision,
            "reason": reason,
            "snapshot_hash": snapshot.snapshot_hash,
            "drift_detected": drift_detected,
        }
        stage.governance_decision_signature = sign_governance_payload(signed_payload, scope="workflow_stage_decision")
        return {
            "decision": decision,
            "reason": reason,
            "approval_required": approval_required,
            "enforcement_mode": mode,
            "snapshot_id": str(snapshot.id),
            "drift_detected": drift_detected,
        }

    async def rollback_stage_policy(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
        actor_id: str,
    ) -> CommercialWorkflowPolicyBinding:
        current_binding, snapshot = await self.ensure_stage_binding(db, execution=execution, stage=stage)
        restored_policy = snapshot.policy_json if snapshot else (((stage.metadata_json or {}).get("policy")) or {})
        rollback_binding = CommercialWorkflowPolicyBinding(
            execution_id=execution.id,
            stage_id=stage.id,
            tenant_id=execution.tenant_id,
            bundle_id=current_binding.bundle_id,
            bundle_ref=current_binding.bundle_ref,
            binding_status="rolled_back",
            enforcement_mode=current_binding.enforcement_mode,
            runtime_policy_hash=current_binding.runtime_policy_hash,
            snapshot_hash=current_binding.snapshot_hash,
            rollback_from_binding_id=current_binding.id,
            immutable_hash=sha256_hex({"rollback_from_binding_id": str(current_binding.id), "policy": restored_policy}),
            metadata_json={"rolled_back_policy": restored_policy},
        )
        db.add(rollback_binding)
        await db.flush()
        await self.ledger.append_event(
            db,
            execution=execution,
            stage_id=stage.id,
            event_type="workflow_rolled_back",
            actor_id=actor_id,
            actor_metadata={"stage_key": stage.stage_key},
            event_summary=f"Policy rollback recorded for stage {stage.stage_key}",
            event_payload={"binding_id": str(rollback_binding.id), "rollback_from_binding_id": str(current_binding.id)},
        )
        return rollback_binding

    async def build_snapshot_view(
        self,
        db: AsyncSession,
        *,
        execution_id,
    ) -> list[dict[str, Any]]:
        rows = (
            await db.execute(
                select(CommercialWorkflowPolicySnapshot)
                .where(CommercialWorkflowPolicySnapshot.execution_id == execution_id)
                .order_by(CommercialWorkflowPolicySnapshot.created_at.asc())
            )
        ).scalars().all()
        return [
            {
                "id": str(row.id),
                "stage_id": str(row.stage_id),
                "binding_id": str(row.binding_id),
                "policy_hash": row.policy_hash,
                "runtime_context_hash": row.runtime_context_hash,
                "snapshot_hash": row.snapshot_hash,
                "metadata": sanitize_report_payload(redact_sensitive_payload(row.metadata_json or {})),
            }
            for row in rows
        ]
