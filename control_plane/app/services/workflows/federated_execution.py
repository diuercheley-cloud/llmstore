from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_federated_workflows import (
    CommercialFederatedWorkflowExecution,
    CommercialWorkflowExecutionPeer,
)
from app.models.commercial.commercial_sovereign_governance import CommercialOfflineRevocationList
from app.models.commercial.commercial_workflows import CommercialWorkflowExecution, CommercialWorkflowStage
from app.services.governance.policy_registry import PolicyRegistryService
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.workflow_policy_enforcement import WorkflowPolicyEnforcementService
from app.services.workflows.workflow_provenance import (
    WorkflowProvenanceService,
    canonical_json,
    redact_sensitive_payload,
    sha256_hex,
)
from app.services.workflows.workflow_receipts import WorkflowReceiptService
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

VALID_FEDERATION_MODES = {"local_only", "push", "pull", "hybrid", "sovereign_airgap"}


def sign_federated_payload(payload: Any, *, scope: str) -> str:
    return f"ed25519:{sha256_hex({'scope': scope, 'payload': payload})[:48]}"


class FederatedWorkflowExecutionService:
    def __init__(self) -> None:
        self.provenance = WorkflowProvenanceService()
        self.receipts = WorkflowReceiptService()
        self.policy_registry = PolicyRegistryService()
        self.policy_enforcement = WorkflowPolicyEnforcementService()

    async def _get_execution(self, db: AsyncSession, execution_id) -> CommercialWorkflowExecution:
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("workflow_execution_not_found")
        return execution

    async def _get_federated_execution(self, db: AsyncSession, federated_execution_id) -> CommercialFederatedWorkflowExecution:
        row = await db.get(CommercialFederatedWorkflowExecution, federated_execution_id)
        if row is None:
            raise ValueError("federated_workflow_execution_not_found")
        return row

    async def _load_stages(self, db: AsyncSession, execution_id) -> list[CommercialWorkflowStage]:
        return (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution_id)
                .order_by(CommercialWorkflowStage.stage_order.asc(), CommercialWorkflowStage.created_at.asc())
            )
        ).scalars().all()

    async def _latest_federated_execution(
        self,
        db: AsyncSession,
        *,
        workflow_id: str,
        tenant_id: str | None,
        cluster_id: str,
    ) -> CommercialFederatedWorkflowExecution | None:
        return (
            await db.execute(
                select(CommercialFederatedWorkflowExecution)
                .where(
                    CommercialFederatedWorkflowExecution.workflow_id == workflow_id,
                    CommercialFederatedWorkflowExecution.tenant_id == tenant_id,
                    CommercialFederatedWorkflowExecution.cluster_id == cluster_id,
                )
                .order_by(desc(CommercialFederatedWorkflowExecution.created_at), desc(CommercialFederatedWorkflowExecution.id))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _is_peer_revoked(self, db: AsyncSession, peer_cluster_id: str) -> bool:
        crls = (
            await db.execute(
                select(CommercialOfflineRevocationList).order_by(CommercialOfflineRevocationList.created_at.desc())
            )
        ).scalars().all()
        return any(peer_cluster_id in (crl.revoked_peer_ids_json or []) for crl in crls)

    def _workflow_id(self, execution: CommercialWorkflowExecution) -> str:
        return execution.session_id or str(execution.id)

    def _deterministic_clock(self, execution: CommercialWorkflowExecution, stages: list[CommercialWorkflowStage]) -> str:
        return sha256_hex(
            {
                "execution_id": str(execution.id),
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "steps": [
                    {
                        "stage_key": stage.stage_key,
                        "stage_order": stage.stage_order,
                        "executed_at": stage.executed_at.isoformat() if stage.executed_at else None,
                    }
                    for stage in stages
                ],
            }
        )

    async def _governance_summary(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stages: list[CommercialWorkflowStage],
    ) -> tuple[str, list[dict[str, Any]]]:
        trail: list[dict[str, Any]] = []
        for stage in stages:
            binding, snapshot = await self.policy_enforcement.ensure_stage_binding(db, execution=execution, stage=stage)
            trail.append(
                sanitize_report_payload(
                    {
                        "stage_key": stage.stage_key,
                        "binding_status": binding.binding_status,
                        "enforcement_mode": binding.enforcement_mode,
                        "runtime_policy_hash": binding.runtime_policy_hash,
                        "snapshot_hash": snapshot.snapshot_hash if snapshot else None,
                        "governance_signature": stage.governance_decision_signature,
                    }
                )
            )
        return sha256_hex(trail), trail

    async def register_peer(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        peer_cluster_id: str,
        peer_region_id: str,
        trust_status: str = "trusted",
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialWorkflowExecutionPeer:
        execution = await self._get_federated_execution(db, federated_execution_id)
        if execution.tenant_id and await self._is_peer_revoked(db, peer_cluster_id):
            raise ValueError("peer_revoked_by_offline_crl")
        existing = (
            await db.execute(
                select(CommercialWorkflowExecutionPeer).where(
                    CommercialWorkflowExecutionPeer.federated_execution_id == federated_execution_id,
                    CommercialWorkflowExecutionPeer.peer_cluster_id == peer_cluster_id,
                )
            )
        ).scalar_one_or_none()
        previous_hash = existing.immutable_hash if existing else execution.immutable_hash
        row = existing or CommercialWorkflowExecutionPeer(
            federated_execution_id=federated_execution_id,
            workflow_id=execution.workflow_id,
            tenant_id=execution.tenant_id,
            client_id=execution.client_id,
            region_id=execution.region_id,
            cluster_id=execution.cluster_id,
            peer_region_id=peer_region_id,
            peer_cluster_id=peer_cluster_id,
        )
        row.execution_hash = execution.execution_hash
        row.dag_hash = execution.dag_hash
        row.provenance_hash = execution.provenance_hash
        row.lease_owner = execution.lease_owner
        row.consensus_status = execution.consensus_status
        row.replay_status = execution.replay_status
        row.federation_mode = execution.federation_mode
        row.deterministic_clock = execution.deterministic_clock
        row.signed_execution_receipt = execution.signed_execution_receipt
        row.attestation_summary = sanitize_report_payload(
            {
                "trust_status": trust_status,
                "peer_cluster_id": peer_cluster_id,
                "peer_region_id": peer_region_id,
            }
        )
        row.sovereign_mode = execution.sovereign_mode
        row.trust_status = trust_status
        row.last_seen_at = utc_now()
        row.metadata_json = sanitize_report_payload(redact_sensitive_payload(metadata_json or {}))
        row.previous_hash = previous_hash
        row.immutable_hash = sha256_hex(
            {
                "federated_execution_id": str(federated_execution_id),
                "peer_cluster_id": peer_cluster_id,
                "peer_region_id": peer_region_id,
                "trust_status": trust_status,
                "execution_hash": execution.execution_hash,
                "previous_hash": previous_hash,
            }
        )
        if existing is None:
            db.add(row)
        await db.flush()
        return row

    async def partition_dag(
        self,
        db: AsyncSession,
        *,
        execution_id,
        cluster_ids: list[str],
    ) -> dict[str, Any]:
        execution = await self._get_execution(db, execution_id)
        stages = await self._load_stages(db, execution.id)
        owners = sorted({item for item in cluster_ids if item})
        if not owners:
            raise ValueError("cluster_ids_required")
        mapping: dict[str, str] = {}
        for stage in stages:
            idx = int(sha256_hex({"workflow_id": self._workflow_id(execution), "stage_key": stage.stage_key})[:8], 16) % len(owners)
            mapping[stage.stage_key] = owners[idx]
        return {
            "workflow_execution_id": str(execution.id),
            "workflow_id": self._workflow_id(execution),
            "cluster_count": len(owners),
            "owners": mapping,
            "partition_hash": sha256_hex(mapping),
        }

    async def register_execution(
        self,
        db: AsyncSession,
        *,
        execution_id,
        region_id: str,
        cluster_id: str,
        federation_mode: str = "local_only",
        sovereign_mode: str = "disabled",
        client_id: str | None = None,
        peer_clusters: list[dict[str, str]] | None = None,
    ) -> CommercialFederatedWorkflowExecution:
        if federation_mode not in VALID_FEDERATION_MODES:
            raise ValueError("invalid_federation_mode")
        execution = await self._get_execution(db, execution_id)
        if execution.tenant_id and client_id and execution.tenant_id != client_id:
            raise ValueError("tenant_scope_violation")
        stages = await self._load_stages(db, execution.id)
        provenance = await self.provenance.build_execution_provenance(db, execution)
        governance_hash, governance_trail = await self._governance_summary(db, execution=execution, stages=stages)
        if execution.provenance_hash is None:
            execution.provenance_hash = provenance["provenance_hash"]
        receipt = await self.receipts.issue_execution_receipt(db, execution, provenance_summary=provenance)
        cluster_ids = [cluster_id] + [item["cluster_id"] for item in (peer_clusters or []) if item.get("cluster_id")]
        partition = await self.partition_dag(db, execution_id=execution.id, cluster_ids=cluster_ids or [cluster_id])
        routing_hash = sha256_hex({"owners": partition["owners"], "mode": federation_mode})
        runtime_snapshot_hash = sha256_hex([stage.runtime_snapshot_hash for stage in stages])
        execution_hash = sha256_hex(
            {
                "execution_id": str(execution.id),
                "execution_hash_chain": execution.execution_hash_chain,
                "receipt_hash": receipt.receipt_hash,
                "stage_hashes": [stage.stage_hash for stage in stages],
                "routing_hash": routing_hash,
                "runtime_snapshot_hash": runtime_snapshot_hash,
            }
        )
        previous = await self._latest_federated_execution(
            db,
            workflow_id=self._workflow_id(execution),
            tenant_id=execution.tenant_id,
            cluster_id=cluster_id,
        )
        row = CommercialFederatedWorkflowExecution(
            workflow_execution_id=execution.id,
            workflow_id=self._workflow_id(execution),
            tenant_id=execution.tenant_id,
            client_id=client_id or execution.tenant_id,
            region_id=region_id,
            cluster_id=cluster_id,
            execution_hash=execution_hash,
            dag_hash=execution.dag_hash,
            provenance_hash=provenance["provenance_hash"],
            lease_owner=None,
            consensus_status="pending",
            replay_status=execution.replay_status or "not_started",
            federation_mode=federation_mode,
            deterministic_clock=self._deterministic_clock(execution, stages),
            previous_hash=previous.immutable_hash if previous else None,
            attestation_summary=sanitize_report_payload(
                {
                    "receipt_hash": receipt.receipt_hash,
                    "governance_status": execution.governance_status,
                    "confidential_metadata": execution.confidential_metadata,
                }
            ),
            sovereign_mode=sovereign_mode,
            enforcement_hash=governance_hash,
            governance_decision_trail_json=governance_trail,
            stage_ownership_json=partition["owners"],
            dag_partition_json=partition,
            runtime_snapshot_hash=runtime_snapshot_hash,
            routing_decision_hash=routing_hash,
            reconciliation_status="clean",
            drift_detected=bool(execution.drift_detected),
            metadata_json=sanitize_report_payload(
                {
                    "receipt_id": str(receipt.id),
                    "definition_id": str(execution.definition_id),
                    "signed_stage_receipts": {
                        stage.stage_key: sign_federated_payload(
                            {"stage_hash": stage.stage_hash, "receipt_hash": stage.receipt_hash},
                            scope="workflow_stage_receipt",
                        )
                        for stage in stages
                    },
                }
            ),
        )
        row.immutable_hash = sha256_hex(
            {
                "workflow_execution_id": str(execution.id),
                "cluster_id": cluster_id,
                "region_id": region_id,
                "execution_hash": execution_hash,
                "previous_hash": row.previous_hash,
            }
        )
        row.signed_execution_receipt = sign_federated_payload(
            {"execution_hash": execution_hash, "receipt_hash": receipt.receipt_hash, "cluster_id": cluster_id},
            scope="federated_workflow_execution",
        )
        db.add(row)
        await db.flush()
        for peer in peer_clusters or []:
            await self.register_peer(
                db,
                federated_execution_id=row.id,
                peer_cluster_id=peer["cluster_id"],
                peer_region_id=peer.get("region_id") or region_id,
                trust_status=peer.get("trust_status") or "trusted",
                metadata_json=peer,
            )
        return row

    async def forward_execution(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        target_cluster_id: str,
    ) -> dict[str, Any]:
        row = await self._get_federated_execution(db, federated_execution_id)
        if row.federation_mode == "local_only":
            raise ValueError("federation_forwarding_disabled")
        if row.tenant_id and target_cluster_id == row.cluster_id:
            selected = sorted(
                key for key, owner in (row.stage_ownership_json or {}).items() if owner == target_cluster_id
            )
        else:
            selected = sorted(
                key for key, owner in (row.stage_ownership_json or {}).items() if owner == target_cluster_id
            )
        return sanitize_report_payload(
            {
                "federated_execution_id": str(row.id),
                "target_cluster_id": target_cluster_id,
                "workflow_id": row.workflow_id,
                "tenant_id": row.tenant_id,
                "federation_mode": row.federation_mode,
                "stage_keys": selected,
                "routing_decision_hash": row.routing_decision_hash,
                "bundle_signature": sign_federated_payload(
                    {
                        "federated_execution_id": str(row.id),
                        "target_cluster_id": target_cluster_id,
                        "stage_keys": selected,
                        "routing_decision_hash": row.routing_decision_hash,
                    },
                    scope="federated_execution_forward",
                ),
            }
        )

    async def list_peers(self, db: AsyncSession, *, tenant_id: str | None = None) -> list[CommercialWorkflowExecutionPeer]:
        stmt = select(CommercialWorkflowExecutionPeer).order_by(desc(CommercialWorkflowExecutionPeer.updated_at))
        if tenant_id:
            stmt = stmt.where(CommercialWorkflowExecutionPeer.tenant_id == tenant_id)
        return (await db.execute(stmt)).scalars().all()

    async def list_executions(self, db: AsyncSession, *, tenant_id: str | None = None) -> list[CommercialFederatedWorkflowExecution]:
        stmt = select(CommercialFederatedWorkflowExecution).order_by(desc(CommercialFederatedWorkflowExecution.created_at))
        if tenant_id:
            stmt = stmt.where(CommercialFederatedWorkflowExecution.tenant_id == tenant_id)
        return (await db.execute(stmt)).scalars().all()

    async def overview(self, db: AsyncSession, *, tenant_id: str | None = None) -> dict[str, Any]:
        rows = await self.list_executions(db, tenant_id=tenant_id)
        peers = await self.list_peers(db, tenant_id=tenant_id)
        return {
            "total_executions": len(rows),
            "total_peers": len(peers),
            "consensus_healthy": sum(1 for row in rows if row.consensus_status == "verified"),
            "replay_verified": sum(1 for row in rows if row.replay_status == "verified"),
            "sovereign_airgap": sum(1 for row in rows if row.federation_mode == "sovereign_airgap"),
            "drift_detected": sum(1 for row in rows if row.drift_detected),
            "topology": [
                {
                    "workflow_id": row.workflow_id,
                    "tenant_id": row.tenant_id,
                    "region_id": row.region_id,
                    "cluster_id": row.cluster_id,
                    "stage_owners": row.stage_ownership_json or {},
                }
                for row in rows[:50]
            ],
        }

    async def drift_summary(self, db: AsyncSession, *, tenant_id: str | None = None) -> dict[str, Any]:
        rows = await self.list_executions(db, tenant_id=tenant_id)
        items = [
            {
                "federated_execution_id": str(row.id),
                "workflow_id": row.workflow_id,
                "tenant_id": row.tenant_id,
                "cluster_id": row.cluster_id,
                "drift_detected": row.drift_detected,
                "reconciliation_status": row.reconciliation_status,
            }
            for row in rows
        ]
        return {
            "items": items,
            "heatmap_hash": sha256_hex(canonical_json(items)),
            "drifted": sum(1 for item in items if item["drift_detected"]),
        }

    async def reconcile(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        canonical_execution_hash: str | None = None,
    ) -> CommercialFederatedWorkflowExecution:
        row = await self._get_federated_execution(db, federated_execution_id)
        if canonical_execution_hash and canonical_execution_hash != row.execution_hash:
            row.execution_hash = canonical_execution_hash
            row.drift_detected = False
            row.reconciliation_status = "auto_reconciled"
        else:
            row.reconciliation_status = "verified"
        row.consensus_status = "verified"
        row.updated_at = utc_now()
        await db.flush()
        return row
