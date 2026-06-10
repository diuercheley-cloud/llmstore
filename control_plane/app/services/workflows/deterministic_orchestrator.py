from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_workflows import (
    CommercialWorkflowDefinition,
    CommercialWorkflowDeterminismReport,
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowReplay,
    CommercialWorkflowReplaySession,
    CommercialWorkflowStage,
)
from app.services.agents.trusted_agent_runtime import TrustedAgentRuntime
from app.services.governance.policy_engine import PolicyEngineService
from app.services.inference.confidential_runtime import log_confidential_audit
from app.services.inference.sovereign_appliance import create_offline_sync_manifest
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.checkpoint_replay import WorkflowCheckpointReplayService
from app.services.workflows.workflow_approval_chain import WorkflowApprovalChainService
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from app.services.workflows.workflow_policy_enforcement import WorkflowPolicyEnforcementService
from app.services.workflows.workflow_provenance import (
    WorkflowProvenanceService,
    canonical_json,
    redact_sensitive_payload,
    sha256_hex,
)
from app.services.workflows.workflow_receipts import WorkflowReceiptService
from app.services.workflows.workflow_replay_sessions import WorkflowReplaySessionService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class DeterministicWorkflowOrchestrator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.policy_engine = PolicyEngineService()
        self.trusted_runtime = TrustedAgentRuntime()
        self.checkpoints = WorkflowCheckpointReplayService()
        self.receipts = WorkflowReceiptService()
        self.provenance = WorkflowProvenanceService()
        self.policy_enforcement = WorkflowPolicyEnforcementService()
        self.approvals = WorkflowApprovalChainService()
        self.governance_ledger = WorkflowGovernanceLedgerService()
        self.replay_sessions = WorkflowReplaySessionService()

    def _normalize_dag(self, dag_or_steps: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        if isinstance(dag_or_steps, dict):
            stages = dag_or_steps.get("stages") or []
            entry_stage = dag_or_steps.get("entry_stage")
        else:
            stages = dag_or_steps
            entry_stage = stages[0]["stage_key"] if stages else None
        normalized_stages: list[dict[str, Any]] = []
        for index, stage in enumerate(stages):
            key = stage.get("stage_key") or stage.get("name") or f"stage-{index}"
            normalized_stages.append(
                {
                    "stage_key": key,
                    "name": stage.get("name") or key,
                    "stage_type": stage.get("stage_type") or stage.get("action") or "task",
                    "dependencies": sorted(stage.get("dependencies") or []),
                    "policy": sanitize_report_payload(stage.get("policy") or {}),
                    "runtime": sanitize_report_payload(stage.get("runtime") or {}),
                    "config": sanitize_report_payload(stage.get("config") or {}),
                    "metadata": sanitize_report_payload(stage.get("metadata") or {}),
                }
            )
        order = self._topological_sort(normalized_stages)
        ordered_stages = [next(stage for stage in normalized_stages if stage["stage_key"] == key) for key in order]
        return {"entry_stage": entry_stage or (order[0] if order else None), "stages": ordered_stages}

    def _topological_sort(self, stages: list[dict[str, Any]]) -> list[str]:
        stage_map = {stage["stage_key"]: stage for stage in stages}
        visited: set[str] = set()
        visiting: set[str] = set()
        order: list[str] = []

        def visit(stage_key: str) -> None:
            if stage_key in visited:
                return
            if stage_key in visiting:
                raise ValueError(f"workflow_cycle_detected:{stage_key}")
            if stage_key not in stage_map:
                raise ValueError(f"workflow_dependency_missing:{stage_key}")
            visiting.add(stage_key)
            for dependency in stage_map[stage_key]["dependencies"]:
                visit(dependency)
            visiting.remove(stage_key)
            visited.add(stage_key)
            order.append(stage_key)

        for stage in sorted(stages, key=lambda item: item["stage_key"]):
            visit(stage["stage_key"])
        return order

    def _definition_hash(self, normalized_dag: dict[str, Any], metadata_json: dict[str, Any] | None) -> str:
        return sha256_hex({"dag": normalized_dag, "metadata": sanitize_report_payload(metadata_json or {})})

    async def create_definition(
        self,
        db: AsyncSession,
        *,
        name: str,
        dag_or_steps: list[dict[str, Any]] | dict[str, Any],
        client_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        workflow_family: str | None = None,
    ) -> CommercialWorkflowDefinition:
        normalized_dag = self._normalize_dag(dag_or_steps)
        definition_hash = self._definition_hash(normalized_dag, metadata_json)
        definition = CommercialWorkflowDefinition(
            workflow_name=name,
            workflow_family=workflow_family or name,
            client_id=client_id,
            steps_config=normalized_dag["stages"],
            dag_json=normalized_dag,
            entry_stage=normalized_dag["entry_stage"],
            definition_hash=definition_hash,
            immutable_hash=sha256_hex({"definition_hash": definition_hash, "created_at": utc_now().isoformat()}),
            offline_compatible=True,
            sovereign_ready=True,
            is_deterministic=True,
            enforce_reproducibility=True,
            metadata_json=sanitize_report_payload(metadata_json or {}),
        )
        db.add(definition)
        await db.flush()
        return definition

    async def start_execution(
        self,
        db: AsyncSession,
        *,
        definition_id,
        session_id: str,
        tenant_id: str | None = None,
        request_id: str | None = None,
        replay_of_execution_id=None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialWorkflowExecution:
        definition = await db.get(CommercialWorkflowDefinition, definition_id)
        if definition is None:
            raise ValueError("workflow_definition_not_found")
        if definition.client_id and tenant_id and definition.client_id != tenant_id:
            raise ValueError("tenant_scope_violation")
        dag_json = definition.dag_json or self._normalize_dag(definition.steps_config)
        stages = dag_json["stages"]
        stage_keys = [stage["stage_key"] for stage in stages]
        execution = CommercialWorkflowExecution(
            definition_id=definition.id,
            replay_of_execution_id=replay_of_execution_id,
            session_id=session_id,
            request_id=request_id,
            tenant_id=tenant_id or definition.client_id,
            status="running",
            execution_mode="deterministic",
            dag_hash=sha256_hex(stage_keys),
            policy_gate_status="pending",
            determinism_status="pending",
            total_steps=len(stages),
            metadata_json=sanitize_report_payload(
                {
                    "trusted_agent_runtime": True,
                    "confidential_runtime": self.settings.commercial_confidential_runtime_enabled,
                    "governance_federation": self.settings.commercial_governance_federation_enabled,
                    "sovereign_appliance_mode": self.settings.commercial_appliance_mode_enabled,
                    "input_metadata": redact_sensitive_payload(metadata_json or {}),
                }
            ),
        )
        db.add(execution)
        await db.flush()
        await self.governance_ledger.append_event(
            db,
            execution=execution,
            event_type="workflow_started",
            actor_id="system",
            actor_metadata={"tenant_id": execution.tenant_id, "session_id": session_id},
            event_summary=f"Workflow execution {execution.id} started",
            event_payload={"definition_id": str(definition.id), "dag_hash": execution.dag_hash},
        )

        if self.settings.commercial_appliance_mode_enabled:
            manifest = await create_offline_sync_manifest(
                db,
                sync_direction="export",
                payload_type="workflow_execution",
                media_uuid=None,
            )
            execution.offline_bundle_hash = manifest.manifest_hash

        previous_stage_hash = None
        for index, stage in enumerate(stages):
            planned_input_hash = sha256_hex(stage["config"])
            trusted_plan_hash = None
            if stage["stage_type"] == "agent_tool":
                _, trusted_plan_hash, graph_hash = self.trusted_runtime.build_deterministic_plan(
                    [
                        {
                            "tool_name": stage["name"],
                            "payload": stage["config"],
                        }
                    ]
                )
                trusted_plan_hash = graph_hash or trusted_plan_hash
            stage_row = CommercialWorkflowStage(
                execution_id=execution.id,
                definition_id=definition.id,
                tenant_id=execution.tenant_id,
                stage_key=stage["stage_key"],
                stage_name=stage["name"],
                stage_type=stage["stage_type"],
                stage_order=index,
                status="pending",
                dependencies_json=stage["dependencies"],
                planned_input_hash=planned_input_hash,
                previous_stage_hash=previous_stage_hash,
                metadata_json={
                    "policy": stage["policy"],
                    "runtime": stage["runtime"],
                    "config": redact_sensitive_payload(stage["config"]),
                    "metadata": stage["metadata"],
                    "trusted_graph_hash": trusted_plan_hash,
                },
            )
            db.add(stage_row)
            previous_stage_hash = sha256_hex(
                {"stage_key": stage_row.stage_key, "planned_input_hash": planned_input_hash, "previous_stage_hash": previous_stage_hash}
            )
        await db.flush()
        for stage_row in (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution.id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        ).scalars().all():
            await self.policy_enforcement.bind_stage_policy(db, execution=execution, stage=stage_row)
        return execution

    async def _evaluate_stage_policy(
        self,
        *,
        stage: CommercialWorkflowStage,
        tenant_id: str | None,
    ) -> dict[str, Any]:
        policy = ((stage.metadata_json or {}).get("policy")) or {}
        decision = {"decision": "allow", "requires_approval": False, "reason": None}
        allowed_tenants = policy.get("allowed_tenants") or []
        if allowed_tenants and tenant_id not in allowed_tenants:
            decision = {"decision": "deny", "requires_approval": False, "reason": "tenant_not_allowed"}
        elif policy.get("require_approval"):
            decision = {"decision": "allow", "requires_approval": True, "reason": "approval_required"}
        elif policy.get("deny_execution"):
            decision = {"decision": "deny", "requires_approval": False, "reason": "policy_denied"}
        return decision

    async def complete_stage(
        self,
        db: AsyncSession,
        *,
        execution_id,
        stage_key: str,
        input_data: Any,
        output_data: Any,
        state_snapshot: dict[str, Any] | None = None,
    ) -> CommercialWorkflowStage:
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("workflow_execution_not_found")
        stage = (
            await db.execute(
                select(CommercialWorkflowStage).where(
                    CommercialWorkflowStage.execution_id == execution.id,
                    CommercialWorkflowStage.stage_key == stage_key,
                )
            )
        ).scalar_one_or_none()
        if stage is None:
            raise ValueError("workflow_stage_not_found")
        if execution.status == "paused":
            raise ValueError("workflow_execution_paused")

        policy_decision = await self.policy_enforcement.evaluate_stage(db, execution=execution, stage=stage)
        in_memory_decision = await self._evaluate_stage_policy(stage=stage, tenant_id=execution.tenant_id)
        stage_policy = ((stage.metadata_json or {}).get("policy")) or {}
        if (
            policy_decision.get("reason") == "missing_valid_policy"
            and not stage_policy
            and in_memory_decision["decision"] == "allow"
        ):
            policy_decision = {
                "decision": "allow",
                "reason": "implicit_deterministic_allow",
                "approval_required": False,
                "enforcement_mode": "compatibility",
                "snapshot_id": None,
                "drift_detected": False,
            }
        decision = {
            **policy_decision,
            "requested_policy": in_memory_decision,
        }
        stage.policy_decision_json = decision
        if decision["decision"] == "deny":
            stage.status = "blocked"
            stage.policy_gate_status = "denied"
            execution.status = "blocked"
            execution.policy_gate_status = "denied"
            execution.governance_status = "blocked"
            execution.determinism_status = "policy_blocked"
            return stage
        if decision["approval_required"]:
            await self.approvals.expire_pending_approvals(db, execution_id=execution.id)
            stage.status = "pending_approval"
            stage.policy_gate_status = "approval_required"
            snapshot = await db.get(CommercialWorkflowPolicySnapshot, stage.active_policy_snapshot_id) if stage.active_policy_snapshot_id else None
            if stage.approval_status != "approved":
                await self.approvals.request_approval(
                    db,
                    execution=execution,
                    stage=stage,
                    snapshot=snapshot,
                    requested_by=(execution.metadata_json or {}).get("requested_by", "system"),
                    approvers=list((((stage.metadata_json or {}).get("policy")) or {}).get("approvers") or ["workflow-approver"]),
                    ttl_seconds=int(((((stage.metadata_json or {}).get("policy")) or {}).get("approval_ttl_seconds")) or 3600),
                    delegated_approvers=list((((stage.metadata_json or {}).get("policy")) or {}).get("delegated_approvers") or []),
                    replay_safe=not bool((((stage.metadata_json or {}).get("policy")) or {}).get("replay_unsafe")),
                    metadata={"stage_key": stage.stage_key},
                )
            if stage.approval_status != "approved":
                execution.governance_status = "approval_required"
                execution.policy_gate_status = "approval_required"
                return stage
            stage.policy_gate_status = "allowed"
            execution.policy_gate_status = "approval_required"
            execution.governance_status = "approved"

        input_hash = sha256_hex(input_data)
        output_hash = sha256_hex(output_data)
        runtime_snapshot_hash = sha256_hex(
            {
                "tenant_id": execution.tenant_id,
                "stage_key": stage.stage_key,
                "request_id": execution.request_id,
                "offline_first": self.settings.commercial_appliance_mode_enabled,
            }
        )
        dependency_hashes = (
            await db.execute(
                select(CommercialWorkflowStage.stage_hash)
                .where(
                    CommercialWorkflowStage.execution_id == execution.id,
                    CommercialWorkflowStage.stage_key.in_(stage.dependencies_json or []),
                )
            )
        ).scalars().all()
        dependency_hashes = sorted([item for item in dependency_hashes if item])
        previous_stage_hash = stage.previous_stage_hash
        stage_hash = sha256_hex(
            {
                "definition_id": str(stage.definition_id),
                "stage_key": stage.stage_key,
                "dependencies": stage.dependencies_json or [],
                "dependency_hashes": dependency_hashes,
                "previous_stage_hash": previous_stage_hash,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "runtime_snapshot_hash": runtime_snapshot_hash,
            }
        )
        stage.input_hash = input_hash
        stage.output_hash = output_hash
        stage.runtime_snapshot_hash = runtime_snapshot_hash
        stage.stage_hash = stage_hash
        stage.lineage_hash = sha256_hex(
            {
                "stage_hash": stage_hash,
                "dependency_hashes": dependency_hashes,
                "previous_stage_hash": previous_stage_hash,
            }
        )
        stage.status = "completed"
        stage.policy_gate_status = "allowed"
        stage.executed_at = utc_now()
        if self.settings.commercial_confidential_runtime_enabled:
            await log_confidential_audit(
                db,
                session_id=None,
                event_type="workflow_stage_completed",
                summary=f"Workflow stage {stage.stage_key} completed with confidential runtime controls",
            )
            stage.confidential_audit_hash = sha256_hex(f"confidential:{stage.stage_key}:{execution.id}")

        checkpoint = await self.checkpoints.create_checkpoint(
            db,
            execution=execution,
            stage=stage,
            step_index=stage.stage_order,
            input_hash=input_hash,
            output_hash=output_hash,
            state_snapshot=redact_sensitive_payload(state_snapshot or {}),
        )
        stage.receipt_hash = sha256_hex(
            {
                "execution_id": str(execution.id),
                "stage_key": stage.stage_key,
                "stage_hash": stage.stage_hash,
                "checkpoint_hash": checkpoint.snapshot_hash,
            }
        )
        execution.current_step_index = max(execution.current_step_index, stage.stage_order + 1)
        execution.execution_hash_chain = sha256_hex(
            {
                "previous_chain": execution.execution_hash_chain,
                "stage_hash": stage.stage_hash,
                "checkpoint_hash": checkpoint.snapshot_hash,
            }
        )
        execution.ledger_hash = sha256_hex(
            {
                "previous_ledger": execution.ledger_hash,
                "stage_receipt_hash": stage.receipt_hash,
                "policy_gate_status": stage.policy_gate_status,
            }
        )
        execution.policy_gate_status = "allowed"
        execution.governance_status = "allowed"
        completed_count = (
            await db.execute(
                select(func.count())
                .select_from(CommercialWorkflowStage)
                .where(
                    CommercialWorkflowStage.execution_id == execution.id,
                    CommercialWorkflowStage.status == "completed",
                )
            )
        ).scalar_one()
        if completed_count >= execution.total_steps:
            execution.status = "completed"
            execution.completed_at = utc_now()
            execution.determinism_status = "verified"
            provenance = await self.provenance.build_execution_provenance(db, execution)
            execution.provenance_hash = provenance["provenance_hash"]
            receipt = await self.receipts.issue_execution_receipt(db, execution, provenance_summary=provenance)
            stage.receipt_hash = receipt.receipt_hash
        return stage

    async def pause_execution(self, db: AsyncSession, execution_id) -> CommercialWorkflowExecution:
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("workflow_execution_not_found")
        execution.status = "paused"
        execution.paused_at = utc_now()
        execution.resume_token_hash = sha256_hex(f"{execution.id}:{execution.last_checkpoint_hash}:{execution.paused_at.isoformat()}")
        return execution

    async def resume_execution(
        self,
        db: AsyncSession,
        execution_id,
        *,
        resume_token: str | None = None,
    ) -> CommercialWorkflowExecution:
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("workflow_execution_not_found")
        if execution.resume_token_hash and resume_token and execution.resume_token_hash != sha256_hex(resume_token):
            raise ValueError("resume_token_invalid")
        execution.status = "running"
        execution.paused_at = None
        return execution

    async def finalize_receipt(self, db: AsyncSession, execution_id):
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("workflow_execution_not_found")
        provenance = await self.provenance.build_execution_provenance(db, execution)
        execution.provenance_hash = provenance["provenance_hash"]
        return await self.receipts.issue_execution_receipt(db, execution, provenance_summary=provenance)

    async def initiate_replay(self, db: AsyncSession, original_execution_id) -> CommercialWorkflowReplay:
        replay = CommercialWorkflowReplay(original_execution_id=original_execution_id, status="pending")
        db.add(replay)
        await db.flush()
        return replay

    async def create_replay_session(
        self,
        db: AsyncSession,
        *,
        original_execution_id,
        requested_by: str,
        replay_execution_id=None,
        tenant_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ):
        original_execution = await db.get(CommercialWorkflowExecution, original_execution_id)
        if original_execution is None:
            raise ValueError("workflow_execution_not_found")
        replay_execution = await db.get(CommercialWorkflowExecution, replay_execution_id) if replay_execution_id else None
        return await self.replay_sessions.create_session(
            db,
            original_execution=original_execution,
            replay_execution=replay_execution,
            tenant_id=tenant_id or original_execution.tenant_id,
            requested_by=requested_by,
            metadata_json=metadata_json,
        )

    async def finalize_replay_session(self, db: AsyncSession, replay_session_id):
        row = await db.get(CommercialWorkflowReplaySession, replay_session_id)
        if row is None:
            raise ValueError("workflow_replay_session_not_found")
        return await self.replay_sessions.complete_session(db, session_row=row)

    async def verify_replay(self, db: AsyncSession, replay_id) -> CommercialWorkflowDeterminismReport:
        replay = await db.get(CommercialWorkflowReplay, replay_id)
        if replay is None:
            raise ValueError("workflow_replay_not_found")
        if replay.replay_execution_id is None:
            raise ValueError("workflow_replay_execution_missing")
        drift = await self.provenance.detect_pipeline_drift(db, replay.original_execution_id, replay.replay_execution_id)
        score = 1.0 if not drift["drift_detected"] else 0.0
        replay.status = "verified" if not drift["drift_detected"] else "drift_detected"
        if drift["mismatches"]:
            replay.mismatched_step_index = drift["mismatches"][0]["stage_index"]
        replay.replay_report = drift
        report = CommercialWorkflowDeterminismReport(
            execution_id=replay.original_execution_id,
            determinism_score=score,
            drift_detected=drift["drift_detected"],
            drift_summary="Perfect determinism verified" if not drift["drift_detected"] else canonical_json(drift),
        )
        db.add(report)
        return report

    async def summarize(self, db: AsyncSession) -> dict[str, Any]:
        definition_count = (await db.execute(select(func.count()).select_from(CommercialWorkflowDefinition))).scalar_one()
        execution_count = (await db.execute(select(func.count()).select_from(CommercialWorkflowExecution))).scalar_one()
        stage_count = (await db.execute(select(func.count()).select_from(CommercialWorkflowStage))).scalar_one()
        receipt_count = (await db.execute(select(func.count()).select_from(CommercialWorkflowStage).where(CommercialWorkflowStage.receipt_hash.is_not(None)))).scalar_one()
        replay_count = (await db.execute(select(func.count()).select_from(CommercialWorkflowReplay))).scalar_one()
        return {
            "enabled": self.settings.commercial_workflow_determinism_enabled,
            "offline_first": True,
            "enforce_reproducibility": True,
            "definitions": definition_count,
            "executions": execution_count,
            "stages": stage_count,
            "stage_receipts": receipt_count,
            "total_definitions": definition_count,
            "total_executions": execution_count,
            "total_replays": replay_count,
        }
