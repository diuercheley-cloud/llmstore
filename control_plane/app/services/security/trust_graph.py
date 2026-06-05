from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, UTC
from typing import Any

from app.models.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionPolicy,
    CommercialAutonomousExecutionReceipt,
    CommercialExecutionBlastRadius,
    CommercialExecutionGuardrailEvent,
    CommercialHumanApprovalCheckpoint,
)
from app.models.commercial_confidential_runtime import (
    CommercialConfidentialInferenceSession,
    CommercialConfidentialRuntimeProfile,
)
from app.models.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_governance_federation import (
    CommercialFederatedAuditTrail,
    CommercialFederatedPolicySync,
    CommercialGovernanceFederationPeer,
)
from app.models.commercial_model_supply_chain import (
    CommercialModelIntegrityScan,
    CommercialRuntimeModelAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.models.commercial_operations_center import CommercialCryptographicTrustSnapshot
from app.models.commercial_runtime_fabric import (
    CommercialRuntimeFabricEvent,
    CommercialRuntimeFabricHealth,
)
from app.models.commercial_sovereign_governance import (
    CommercialAirgapSyncPackage,
    CommercialHardwareAttestationRecord,
)
from app.models.commercial_trust_graph import CommercialTrustGraphEdge, CommercialTrustGraphNode
from app.models.commercial_workflows import (
    CommercialWorkflowDefinition,
    CommercialWorkflowExecution,
    CommercialWorkflowPolicyBinding,
    CommercialWorkflowReceipt,
    CommercialWorkflowStage,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256(payload: Any) -> str:
    if not isinstance(payload, str):
        payload = _canonical_json(payload)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _merkle_root(parts: list[str]) -> str:
    if not parts:
        return _sha256("empty")
    level = sorted(parts)
    while len(level) > 1:
        next_level: list[str] = []
        for idx in range(0, len(level), 2):
            left = level[idx]
            right = level[idx + 1] if idx + 1 < len(level) else left
            next_level.append(_sha256(f"{left}:{right}"))
        level = next_level
    return level[0]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _sanitize(payload: dict[str, Any] | None) -> dict[str, Any]:
    return sanitize_report_payload(payload or {})


def _tenant_matches(value: Any, tenant_id: str | None) -> bool:
    if tenant_id is None:
        return True
    if value is None:
        return True
    return str(value) == str(tenant_id)


class TrustGraphService:
    async def _safe_scalars(self, db: AsyncSession, statement) -> list[Any]:
        try:
            return (await db.execute(statement)).scalars().all()
        except SQLAlchemyError:
            return []

    def calculate_node_hash(
        self,
        node_type: str,
        label: str,
        metadata: dict[str, Any],
        external_id: str | None = None,
    ) -> str:
        return _sha256(
            {
                "external_id": external_id,
                "label": label,
                "metadata": _sanitize(metadata),
                "node_type": node_type,
            }
        )

    def calculate_edge_hash(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        metadata: dict[str, Any],
    ) -> str:
        return _sha256(
            {
                "edge_type": edge_type,
                "metadata": _sanitize(metadata),
                "source_id": str(source_id),
                "target_id": str(target_id),
            }
        )

    async def add_node(
        self,
        db: AsyncSession,
        node_type: str,
        label: str,
        metadata: dict[str, Any],
        external_id: str | None = None,
    ) -> CommercialTrustGraphNode:
        sanitized_metadata = _sanitize(metadata)
        node_hash = self.calculate_node_hash(node_type, label, sanitized_metadata, external_id)
        existing = (
            await db.execute(
                select(CommercialTrustGraphNode).where(
                    CommercialTrustGraphNode.hash == node_hash,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        node = CommercialTrustGraphNode(
            node_type=node_type,
            label=label,
            metadata_json=sanitized_metadata,
            hash=node_hash,
            external_id=external_id,
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    async def add_edge(
        self,
        db: AsyncSession,
        source_node_id: Any,
        target_node_id: Any,
        edge_type: str,
        metadata: dict[str, Any],
    ) -> CommercialTrustGraphEdge:
        sanitized_metadata = _sanitize(metadata)
        edge_hash = self.calculate_edge_hash(str(source_node_id), str(target_node_id), edge_type, sanitized_metadata)
        existing = (
            await db.execute(
                select(CommercialTrustGraphEdge).where(
                    CommercialTrustGraphEdge.hash == edge_hash,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        edge = CommercialTrustGraphEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            metadata_json=sanitized_metadata,
            hash=edge_hash,
        )
        db.add(edge)
        await db.commit()
        await db.refresh(edge)
        return edge

    async def _load_manual_graph(self, db: AsyncSession) -> dict[str, Any]:
        nodes = await self._safe_scalars(db, select(CommercialTrustGraphNode))
        edges = await self._safe_scalars(db, select(CommercialTrustGraphEdge))
        return {
            "nodes": [
                {
                    "id": str(node.id),
                    "type": node.node_type,
                    "label": node.label,
                    "metadata": _sanitize(node.metadata_json or {}),
                    "hash": node.hash,
                    "source": "manual",
                    "created_at": _iso(node.created_at),
                    "external_id": node.external_id,
                }
                for node in nodes
            ],
            "edges": [
                {
                    "id": str(edge.id),
                    "source": str(edge.source_node_id),
                    "target": str(edge.target_node_id),
                    "type": edge.edge_type,
                    "metadata": _sanitize(edge.metadata_json or {}),
                    "hash": edge.hash,
                    "source_kind": "manual",
                    "created_at": _iso(edge.created_at),
                }
                for edge in edges
            ],
        }

    async def _build_derived_graph(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
        redact_sovereign: bool = True,
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        node_index: dict[str, dict[str, Any]] = {}
        stage_ids: dict[tuple[str, str], str] = {}
        receipt_ids_by_hash: dict[str, str] = {}
        workflow_receipt_ids_by_hash: dict[str, str] = {}
        policy_node_ids_by_db_id: dict[str, str] = {}
        peer_node_ids_by_cluster: dict[str, str] = {}
        runtime_node_ids_by_key: dict[str, str] = {}
        model_node_ids_by_registry: dict[str, str] = {}
        confidential_profile_ids: dict[str, str] = {}
        autonomous_policy_node_ids: dict[str, str] = {}
        autonomous_checkpoint_ids: dict[str, str] = {}
        autonomous_event_ids: dict[str, str] = {}
        autonomous_blast_ids: dict[str, str] = {}
        autonomous_receipt_ids_by_hash: dict[str, str] = {}

        def add_node(
            node_type: str,
            external_id: str,
            label: str,
            metadata: dict[str, Any],
        ) -> str:
            sanitized_metadata = _sanitize(metadata)
            node_hash = self.calculate_node_hash(node_type, label, sanitized_metadata, external_id)
            node_id = f"{node_type}:{external_id}"
            node_index[node_id] = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "metadata": sanitized_metadata,
                "hash": node_hash,
                "external_id": external_id,
                "source": "derived",
            }
            return node_id

        def add_edge(
            source: str,
            target: str,
            edge_type: str,
            metadata: dict[str, Any],
        ) -> None:
            if source == target:
                return
            sanitized_metadata = _sanitize(metadata)
            edge_hash = self.calculate_edge_hash(source, target, edge_type, sanitized_metadata)
            edges.append(
                {
                    "id": f"{edge_type}:{source}:{target}",
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "metadata": sanitized_metadata,
                    "hash": edge_hash,
                    "source_kind": "derived",
                }
            )

        policy_bundles = await self._safe_scalars(
            db,
            select(CommercialPolicyBundle).order_by(
                CommercialPolicyBundle.bundle_name.asc(),
                CommercialPolicyBundle.bundle_version.asc(),
            ),
        )
        for bundle in policy_bundles:
            if not _tenant_matches(bundle.client_id, tenant_id):
                continue
            node_id = add_node(
                "governance",
                f"policy-bundle:{bundle.id}",
                bundle.bundle_name,
                {
                    "bundle_type": bundle.bundle_type,
                    "bundle_version": bundle.bundle_version,
                    "client_id": str(bundle.client_id) if bundle.client_id else None,
                    "immutable_hash": bundle.immutable_hash,
                    "mode": bundle.mode,
                    "status": bundle.status,
                },
            )
            policy_node_ids_by_db_id[str(bundle.id)] = node_id

        peers = await self._safe_scalars(
            db,
            select(CommercialGovernanceFederationPeer).order_by(
                CommercialGovernanceFederationPeer.peer_cluster_id.asc()
            ),
        )
        for peer in peers:
            node_id = add_node(
                "federation",
                f"peer:{peer.peer_cluster_id}",
                peer.peer_cluster_id,
                {
                    "environment": peer.environment,
                    "last_audit_sync_at": _iso(peer.last_audit_sync_at),
                    "last_policy_sync_at": _iso(peer.last_policy_sync_at),
                    "region": peer.region,
                    "status": peer.status,
                    "sync_mode": peer.sync_mode,
                    "trust_level": peer.trust_level,
                },
            )
            peer_node_ids_by_cluster[peer.peer_cluster_id] = node_id

        federated_syncs = await self._safe_scalars(
            db,
            select(CommercialFederatedPolicySync).order_by(CommercialFederatedPolicySync.created_at.asc()),
        )
        for sync in federated_syncs:
            target_id = peer_node_ids_by_cluster.get(sync.target_cluster_id)
            if target_id is None:
                continue
            if sync.bundle_id is not None and str(sync.bundle_id) in policy_node_ids_by_db_id:
                add_edge(
                    policy_node_ids_by_db_id[str(sync.bundle_id)],
                    target_id,
                    "federation_mapping",
                    {
                        "bundle_version": sync.bundle_version,
                        "records_synced": sync.records_synced,
                        "source_hash": sync.source_hash,
                        "status": sync.status,
                        "sync_direction": sync.sync_direction,
                    },
                )

        federated_audits = await self._safe_scalars(
            db,
            select(CommercialFederatedAuditTrail).order_by(CommercialFederatedAuditTrail.received_at.asc()),
        )
        for audit in federated_audits:
            peer_id = peer_node_ids_by_cluster.get(audit.source_cluster_id)
            if peer_id is None:
                continue
            audit_node_id = add_node(
                "federation",
                f"audit:{audit.id}",
                audit.event_type,
                {
                    "dedupe_key": audit.dedupe_key,
                    "event_hash": audit.event_hash,
                    "received_at": _iso(audit.received_at),
                    "source_cluster_id": audit.source_cluster_id,
                },
            )
            add_edge(peer_id, audit_node_id, "audit_event", {"event_type": audit.event_type})

        runtime_health = await self._safe_scalars(
            db,
            select(CommercialRuntimeFabricHealth).order_by(
                CommercialRuntimeFabricHealth.node_id.asc()
            ),
        )
        for row in runtime_health:
            node_id = add_node(
                "runtime",
                f"fabric-health:{row.node_id}",
                row.node_id,
                {
                    "degraded_mode_active": row.degraded_mode_active,
                    "metrics": row.metrics or {},
                    "node_id": row.node_id,
                    "quorum_status": row.quarum_status,
                    "status": row.status,
                },
            )
            runtime_node_ids_by_key[row.node_id] = node_id

        runtime_events = await self._safe_scalars(
            db,
            select(CommercialRuntimeFabricEvent).order_by(CommercialRuntimeFabricEvent.created_at.asc()),
        )
        for event in runtime_events:
            event_id = add_node(
                "runtime",
                f"fabric-event:{event.id}",
                event.event_type or "runtime_event",
                {
                    "component": event.component,
                    "created_at": _iso(event.created_at),
                    "details": event.details or {},
                    "severity": event.severity,
                    "signature": event.signature,
                    "source_node_id": event.source_node_id,
                },
            )
            runtime_id = runtime_node_ids_by_key.get(event.source_node_id)
            if runtime_id is not None:
                add_edge(runtime_id, event_id, "runtime_trust_propagation", {"component": event.component})

        workflow_definitions = await self._safe_scalars(
            db,
            select(CommercialWorkflowDefinition).order_by(
                CommercialWorkflowDefinition.workflow_name.asc(),
                CommercialWorkflowDefinition.version.asc(),
            ),
        )
        workflow_definition_ids: dict[str, str] = {}
        for definition in workflow_definitions:
            if not _tenant_matches(definition.client_id, tenant_id):
                continue
            node_id = add_node(
                "workflow",
                f"workflow-definition:{definition.id}",
                definition.workflow_name,
                {
                    "client_id": definition.client_id,
                    "definition_hash": definition.definition_hash,
                    "entry_stage": definition.entry_stage,
                    "is_deterministic": definition.is_deterministic,
                    "offline_compatible": definition.offline_compatible,
                    "policy_bundle_ref": definition.policy_bundle_ref,
                    "sovereign_ready": definition.sovereign_ready,
                    "version": definition.version,
                },
            )
            workflow_definition_ids[str(definition.id)] = node_id

        workflow_executions = await self._safe_scalars(
            db,
            select(CommercialWorkflowExecution).order_by(CommercialWorkflowExecution.started_at.asc()),
        )
        workflow_execution_ids: dict[str, str] = {}
        for execution in workflow_executions:
            if not _tenant_matches(execution.tenant_id, tenant_id):
                continue
            node_id = add_node(
                "workflow",
                f"workflow-execution:{execution.id}",
                f"execution:{execution.id}",
                {
                    "confidential_metadata": execution.confidential_metadata,
                    "dag_hash": execution.dag_hash,
                    "determinism_status": execution.determinism_status,
                    "drift_detected": execution.drift_detected,
                    "governance_status": execution.governance_status,
                    "offline_bundle_hash": execution.offline_bundle_hash,
                    "policy_gate_status": execution.policy_gate_status,
                    "replay_of_execution_id": str(execution.replay_of_execution_id) if execution.replay_of_execution_id else None,
                    "replay_status": execution.replay_status,
                    "status": execution.status,
                    "tenant_id": execution.tenant_id,
                    "total_steps": execution.total_steps,
                },
            )
            workflow_execution_ids[str(execution.id)] = node_id
            definition_id = workflow_definition_ids.get(str(execution.definition_id))
            if definition_id is not None:
                add_edge(definition_id, node_id, "lineage", {"scope": "definition_execution"})
            if execution.replay_of_execution_id is not None:
                replay_parent = workflow_execution_ids.get(str(execution.replay_of_execution_id))
                if replay_parent is not None:
                    add_edge(replay_parent, node_id, "replay_lineage", {"status": execution.replay_status})

        workflow_stages = await self._safe_scalars(
            db,
            select(CommercialWorkflowStage).order_by(
                CommercialWorkflowStage.execution_id.asc(),
                CommercialWorkflowStage.stage_order.asc(),
            ),
        )
        for stage in workflow_stages:
            if not _tenant_matches(stage.tenant_id, tenant_id):
                continue
            execution_id = workflow_execution_ids.get(str(stage.execution_id))
            if execution_id is None:
                continue
            stage_node_id = add_node(
                "workflow",
                f"workflow-stage:{stage.id}",
                stage.stage_name or stage.stage_key,
                {
                    "approval_status": stage.approval_status,
                    "checkpoint_hash": stage.checkpoint_hash,
                    "drift_status": stage.drift_status,
                    "lineage_hash": stage.lineage_hash,
                    "output_hash": stage.output_hash,
                    "policy_gate_status": stage.policy_gate_status,
                    "previous_stage_hash": stage.previous_stage_hash,
                    "receipt_hash": stage.receipt_hash,
                    "runtime_snapshot_hash": stage.runtime_snapshot_hash,
                    "stage_key": stage.stage_key,
                    "stage_order": stage.stage_order,
                    "stage_type": stage.stage_type,
                    "status": stage.status,
                    "tenant_id": stage.tenant_id,
                },
            )
            stage_ids[(str(stage.execution_id), stage.stage_key)] = stage_node_id
            add_edge(execution_id, stage_node_id, "lineage", {"scope": "execution_stage"})

        for stage in workflow_stages:
            if not _tenant_matches(stage.tenant_id, tenant_id):
                continue
            current_stage = stage_ids.get((str(stage.execution_id), stage.stage_key))
            if current_stage is None:
                continue
            for dependency in sorted(stage.dependencies_json or []):
                dependency_stage = stage_ids.get((str(stage.execution_id), dependency))
                if dependency_stage is not None:
                    add_edge(dependency_stage, current_stage, "dependency_integrity", {"dependency": dependency})

        workflow_receipts = await self._safe_scalars(
            db,
            select(CommercialWorkflowReceipt).order_by(CommercialWorkflowReceipt.created_at.asc()),
        )
        for receipt in workflow_receipts:
            if not _tenant_matches(receipt.tenant_id, tenant_id):
                continue
            node_id = add_node(
                "receipt",
                f"workflow-receipt:{receipt.id}",
                receipt.receipt_hash[:18],
                {
                    "execution_id": str(receipt.execution_id),
                    "immutable_hash": receipt.immutable_hash,
                    "previous_receipt_hash": receipt.previous_receipt_hash,
                    "provenance_hash": receipt.provenance_hash,
                    "tenant_id": receipt.tenant_id,
                    "verification_status": receipt.verification_status,
                },
            )
            workflow_receipt_ids_by_hash[receipt.receipt_hash] = node_id
            execution_id = workflow_execution_ids.get(str(receipt.execution_id))
            if execution_id is not None:
                add_edge(execution_id, node_id, "receipt_chain", {"scope": "workflow"})

        for receipt in workflow_receipts:
            current = workflow_receipt_ids_by_hash.get(receipt.receipt_hash)
            previous = workflow_receipt_ids_by_hash.get(receipt.previous_receipt_hash or "")
            if current is not None and previous is not None:
                add_edge(previous, current, "lineage", {"scope": "workflow_receipt"})

        workflow_bindings = await self._safe_scalars(
            db,
            select(CommercialWorkflowPolicyBinding).order_by(CommercialWorkflowPolicyBinding.created_at.asc()),
        )
        for binding in workflow_bindings:
            stage_node = stage_ids.get((str(binding.execution_id), next(
                (
                    stage.stage_key
                    for stage in workflow_stages
                    if str(stage.id) == str(binding.stage_id)
                ),
                "",
            )))
            bundle_node = policy_node_ids_by_db_id.get(str(binding.bundle_id)) if binding.bundle_id is not None else None
            if stage_node is not None and bundle_node is not None:
                add_edge(bundle_node, stage_node, "governance_binding", {"binding_status": binding.binding_status})

        inference_receipts = await self._safe_scalars(
            db,
            select(CommercialInferenceReceipt).order_by(CommercialInferenceReceipt.created_at.asc()),
        )
        for receipt in inference_receipts:
            if not _tenant_matches(receipt.client_id, tenant_id):
                continue
            node_id = add_node(
                "receipt",
                f"inference-receipt:{receipt.id}",
                receipt.receipt_hash[:18],
                {
                    "client_id": receipt.client_id,
                    "immutable_hash": receipt.immutable_hash,
                    "model_name": receipt.model_name,
                    "previous_receipt_hash": receipt.previous_receipt_hash,
                    "runtime_snapshot_hash": receipt.runtime_snapshot_hash,
                    "timestamp_mode": receipt.timestamp_mode,
                    "verification_status": receipt.verification_status,
                },
            )
            receipt_ids_by_hash[receipt.receipt_hash] = node_id

        for receipt in inference_receipts:
            current_id = receipt_ids_by_hash.get(receipt.receipt_hash)
            previous_id = receipt_ids_by_hash.get(receipt.previous_receipt_hash or "")
            if current_id is not None and previous_id is not None:
                add_edge(previous_id, current_id, "lineage", {"scope": "inference_receipt"})

        airgap_packages = await self._safe_scalars(
            db,
            select(CommercialAirgapSyncPackage).order_by(CommercialAirgapSyncPackage.created_at.asc()),
        )
        for package in airgap_packages:
            metadata = {
                "manifest_hash": package.manifest_hash if not redact_sovereign else f"redacted:{package.manifest_hash[:16]}",
                "package_type": package.package_type,
                "package_version": package.package_version,
                "source_cluster_id": package.source_cluster_id,
                "status": package.status,
                "target_cluster_id": package.target_cluster_id,
            }
            package_id = add_node(
                "sovereign",
                f"airgap-package:{package.id}",
                package.package_type,
                metadata,
            )
            if package.target_cluster_id and package.target_cluster_id in peer_node_ids_by_cluster:
                add_edge(
                    package_id,
                    peer_node_ids_by_cluster[package.target_cluster_id],
                    "sovereign_isolation",
                    {"status": package.status},
                )

        hardware_attestations = await self._safe_scalars(
            db,
            select(CommercialHardwareAttestationRecord).order_by(
                CommercialHardwareAttestationRecord.created_at.asc()
            ),
        )
        for attestation in hardware_attestations:
            node_id = add_node(
                "sovereign",
                f"hardware-attestation:{attestation.id}",
                attestation.node_id or attestation.cluster_id,
                {
                    "attestation_type": attestation.attestation_type,
                    "cluster_id": attestation.cluster_id,
                    "evidence_hash": attestation.evidence_hash if not redact_sovereign else f"redacted:{attestation.evidence_hash[:16]}",
                    "node_id": attestation.node_id,
                    "status": attestation.status,
                    "verified_at": _iso(attestation.verified_at),
                },
            )
            if attestation.node_id and attestation.node_id in runtime_node_ids_by_key:
                add_edge(runtime_node_ids_by_key[attestation.node_id], node_id, "sovereign_isolation", {"status": attestation.status})

        confidential_profiles = await self._safe_scalars(
            db,
            select(CommercialConfidentialRuntimeProfile).order_by(
                CommercialConfidentialRuntimeProfile.profile_name.asc()
            ),
        )
        for profile in confidential_profiles:
            if not _tenant_matches(profile.client_id, tenant_id):
                continue
            node_id = add_node(
                "confidential",
                f"confidential-profile:{profile.id}",
                profile.profile_name,
                {
                    "client_id": profile.client_id,
                    "enabled": profile.enabled,
                    "prohibit_prompt_logging": profile.prohibit_prompt_logging,
                    "prohibit_response_logging": profile.prohibit_response_logging,
                    "require_encrypted_input": profile.require_encrypted_input,
                    "require_model_trust": profile.require_model_trust,
                },
            )
            confidential_profile_ids[str(profile.id)] = node_id

        confidential_sessions = await self._safe_scalars(
            db,
            select(CommercialConfidentialInferenceSession).order_by(
                CommercialConfidentialInferenceSession.created_at.asc()
            ),
        )
        for session in confidential_sessions:
            if not _tenant_matches(session.client_id, tenant_id):
                continue
            node_id = add_node(
                "confidential",
                f"confidential-session:{session.id}",
                f"session:{session.id}",
                {
                    "attestation_status": session.attestation_status,
                    "client_id": session.client_id,
                    "input_mode": session.input_mode,
                    "model_trust_state": session.model_trust_state,
                    "output_mode": session.output_mode,
                    "profile_id": str(session.profile_id) if session.profile_id else None,
                    "retention_policy_applied": session.retention_policy_applied,
                },
            )
            if session.profile_id is not None and str(session.profile_id) in confidential_profile_ids:
                add_edge(confidential_profile_ids[str(session.profile_id)], node_id, "lineage", {"scope": "confidential_session"})

        model_registry = await self._safe_scalars(
            db,
            select(CommercialSignedModelRegistryEntry).order_by(
                CommercialSignedModelRegistryEntry.model_name.asc()
            ),
        )
        for entry in model_registry:
            node_id = add_node(
                "supply_chain",
                f"model-registry:{entry.id}",
                entry.model_name,
                {
                    "approved_by": entry.approved_by,
                    "checksum_sha256": f"redacted:{entry.checksum_sha256[:16]}",
                    "manifest_hash": f"redacted:{entry.manifest_hash[:16]}",
                    "model_alias": entry.model_alias,
                    "model_format": entry.model_format,
                    "provider": entry.provider,
                    "trust_state": entry.trust_state,
                    "tenant_scope_json": entry.tenant_scope_json or {},
                },
            )
            model_node_ids_by_registry[str(entry.id)] = node_id

        model_scans = await self._safe_scalars(
            db,
            select(CommercialModelIntegrityScan).order_by(CommercialModelIntegrityScan.created_at.asc()),
        )
        for scan in model_scans:
            node_id = add_node(
                "supply_chain",
                f"model-scan:{scan.id}",
                scan.model_name,
                {
                    "cluster_id": scan.cluster_id,
                    "integrity_status": scan.integrity_status,
                    "node_id": scan.node_id,
                    "observed_checksum": f"redacted:{(scan.observed_checksum or '')[:16]}" if scan.observed_checksum else None,
                    "scan_type": scan.scan_type,
                },
            )
            registry_id = model_node_ids_by_registry.get(str(scan.registry_entry_id)) if scan.registry_entry_id else None
            if registry_id is not None:
                add_edge(registry_id, node_id, "dependency_integrity", {"integrity_status": scan.integrity_status})

        model_attestations = await self._safe_scalars(
            db,
            select(CommercialRuntimeModelAttestation).order_by(CommercialRuntimeModelAttestation.attested_at.asc()),
        )
        for attestation in model_attestations:
            node_id = add_node(
                "supply_chain",
                f"runtime-model-attestation:{attestation.id}",
                attestation.model_name,
                {
                    "attestation_status": attestation.attestation_status,
                    "backend_name": attestation.backend_name,
                    "cluster_id": attestation.cluster_id,
                    "node_id": attestation.node_id,
                },
            )
            registry_id = model_node_ids_by_registry.get(str(attestation.registry_entry_id)) if attestation.registry_entry_id else None
            if registry_id is not None:
                add_edge(registry_id, node_id, "runtime_trust_propagation", {"attestation_status": attestation.attestation_status})
            if attestation.node_id and attestation.node_id in runtime_node_ids_by_key:
                add_edge(runtime_node_ids_by_key[attestation.node_id], node_id, "dependency_integrity", {"model_name": attestation.model_name})

        autonomous_policies = await self._safe_scalars(
            db,
            select(CommercialAutonomousExecutionPolicy).order_by(
                CommercialAutonomousExecutionPolicy.created_at.asc(),
                CommercialAutonomousExecutionPolicy.policy_name.asc(),
            ),
        )
        for policy in autonomous_policies:
            if not _tenant_matches(policy.tenant_id, tenant_id):
                continue
            policy_node_id = add_node(
                "governance",
                f"autonomous-policy:{policy.id}",
                policy.policy_name,
                {
                    "action_type": policy.action_type,
                    "approval_stages_json": policy.approval_stages_json or [],
                    "guarded_window_end": policy.guarded_window_end,
                    "guarded_window_start": policy.guarded_window_start,
                    "is_active": policy.is_active,
                    "max_blast_radius_score": policy.max_blast_radius_score,
                    "mode": policy.mode,
                    "require_human_approval": policy.require_human_approval,
                    "require_signed_model_promotion": policy.require_signed_model_promotion,
                    "rollback_allowed": policy.rollback_allowed,
                    "runtime_freeze_enabled": policy.runtime_freeze_enabled,
                    "sovereign_hard_stop": policy.sovereign_hard_stop,
                    "tenant_id": policy.tenant_id,
                },
            )
            autonomous_policy_node_ids[str(policy.id)] = policy_node_id
            if policy.policy_bundle_id is not None and str(policy.policy_bundle_id) in policy_node_ids_by_db_id:
                add_edge(
                    policy_node_ids_by_db_id[str(policy.policy_bundle_id)],
                    policy_node_id,
                    "governance_binding",
                    {"scope": "autonomous_execution"},
                )

        blast_radius_rows = await self._safe_scalars(
            db,
            select(CommercialExecutionBlastRadius).order_by(CommercialExecutionBlastRadius.created_at.asc()),
        )
        for blast in blast_radius_rows:
            if not _tenant_matches(blast.tenant_id, tenant_id):
                continue
            blast_node_id = add_node(
                "guardrail",
                f"autonomous-blast-radius:{blast.id}",
                f"{blast.action_type}:{blast.severity}",
                {
                    "action_type": blast.action_type,
                    "blocked": blast.blocked,
                    "cluster_id": blast.cluster_id,
                    "reproducibility_hash": blast.reproducibility_hash,
                    "risk_vector_json": blast.risk_vector_json or {},
                    "scope_json": blast.scope_json or {},
                    "severity": blast.severity,
                    "target_id": blast.target_id,
                    "target_type": blast.target_type,
                    "tenant_id": blast.tenant_id,
                },
            )
            autonomous_blast_ids[str(blast.id)] = blast_node_id

        checkpoints = await self._safe_scalars(
            db,
            select(CommercialHumanApprovalCheckpoint).order_by(
                CommercialHumanApprovalCheckpoint.created_at.asc(),
                CommercialHumanApprovalCheckpoint.checkpoint_stage.asc(),
            ),
        )
        last_checkpoint_by_target: dict[tuple[str | None, str, str | None], str] = {}
        for checkpoint in checkpoints:
            if not _tenant_matches(checkpoint.tenant_id, tenant_id):
                continue
            checkpoint_node_id = add_node(
                "guardrail",
                f"human-checkpoint:{checkpoint.id}",
                f"approval-stage:{checkpoint.checkpoint_stage}",
                {
                    "action_type": checkpoint.action_type,
                    "checkpoint_stage": checkpoint.checkpoint_stage,
                    "immutable_hash": checkpoint.immutable_hash,
                    "required_approvals": checkpoint.required_approvals,
                    "status": checkpoint.status,
                    "target_id": checkpoint.target_id,
                    "target_type": checkpoint.target_type,
                    "tenant_id": checkpoint.tenant_id,
                },
            )
            autonomous_checkpoint_ids[str(checkpoint.id)] = checkpoint_node_id
            if checkpoint.policy_id is not None and str(checkpoint.policy_id) in autonomous_policy_node_ids:
                add_edge(
                    autonomous_policy_node_ids[str(checkpoint.policy_id)],
                    checkpoint_node_id,
                    "approval_chain",
                    {"stage": checkpoint.checkpoint_stage, "status": checkpoint.status},
                )
            target_key = (checkpoint.tenant_id, checkpoint.target_type, checkpoint.target_id)
            previous_checkpoint = last_checkpoint_by_target.get(target_key)
            if previous_checkpoint is not None:
                add_edge(previous_checkpoint, checkpoint_node_id, "lineage", {"scope": "human_approval_chain"})
            last_checkpoint_by_target[target_key] = checkpoint_node_id

        guardrail_events = await self._safe_scalars(
            db,
            select(CommercialExecutionGuardrailEvent).order_by(CommercialExecutionGuardrailEvent.created_at.asc()),
        )
        for event in guardrail_events:
            if not _tenant_matches(event.tenant_id, tenant_id):
                continue
            event_node_id = add_node(
                "guardrail",
                f"guardrail-event:{event.id}",
                event.event_type,
                {
                    "action_type": event.action_type,
                    "decision": event.decision,
                    "immutable_hash": event.immutable_hash,
                    "severity": event.severity,
                    "summary": event.summary,
                    "target_id": event.target_id,
                    "target_type": event.target_type,
                    "tenant_id": event.tenant_id,
                },
            )
            autonomous_event_ids[str(event.id)] = event_node_id
            runtime_node_id = runtime_node_ids_by_key.get((event.details_json or {}).get("node_id") or "")
            if runtime_node_id is not None:
                add_edge(runtime_node_id, event_node_id, "runtime_trust_propagation", {"decision": event.decision})

        autonomous_receipts = await self._safe_scalars(
            db,
            select(CommercialAutonomousExecutionReceipt).order_by(CommercialAutonomousExecutionReceipt.created_at.asc()),
        )
        for receipt in autonomous_receipts:
            if not _tenant_matches(receipt.tenant_id, tenant_id):
                continue
            receipt_node_id = add_node(
                "receipt",
                f"autonomous-receipt:{receipt.id}",
                receipt.receipt_hash[:18],
                {
                    "action_type": receipt.action_type,
                    "approval_hash": receipt.approval_hash,
                    "decision": receipt.decision,
                    "immutable_hash": receipt.immutable_hash,
                    "previous_receipt_hash": receipt.previous_receipt_hash,
                    "runtime_hash": receipt.runtime_hash,
                    "target_id": receipt.target_id,
                    "target_type": receipt.target_type,
                    "tenant_id": receipt.tenant_id,
                    "verification_status": receipt.verification_status,
                },
            )
            autonomous_receipt_ids_by_hash[receipt.receipt_hash] = receipt_node_id
            if receipt.policy_id is not None and str(receipt.policy_id) in autonomous_policy_node_ids:
                add_edge(
                    autonomous_policy_node_ids[str(receipt.policy_id)],
                    receipt_node_id,
                    "receipt_chain",
                    {"scope": "autonomous_execution"},
                )
            if receipt.checkpoint_id is not None and str(receipt.checkpoint_id) in autonomous_checkpoint_ids:
                add_edge(
                    autonomous_checkpoint_ids[str(receipt.checkpoint_id)],
                    receipt_node_id,
                    "approval_chain",
                    {"scope": "checkpoint_receipt"},
                )
            if receipt.blast_radius_id is not None and str(receipt.blast_radius_id) in autonomous_blast_ids:
                add_edge(
                    autonomous_blast_ids[str(receipt.blast_radius_id)],
                    receipt_node_id,
                    "dependency_integrity",
                    {"scope": "blast_radius_receipt"},
                )
            if receipt.guardrail_event_id is not None and str(receipt.guardrail_event_id) in autonomous_event_ids:
                add_edge(
                    autonomous_event_ids[str(receipt.guardrail_event_id)],
                    receipt_node_id,
                    "receipt_chain",
                    {"scope": "guardrail_event_receipt"},
                )

        for receipt in autonomous_receipts:
            current = autonomous_receipt_ids_by_hash.get(receipt.receipt_hash)
            previous = autonomous_receipt_ids_by_hash.get(receipt.previous_receipt_hash or "")
            if current is not None and previous is not None:
                add_edge(previous, current, "lineage", {"scope": "autonomous_receipt"})

        snapshots = await self._safe_scalars(
            db,
            select(CommercialCryptographicTrustSnapshot).order_by(
                CommercialCryptographicTrustSnapshot.created_at.asc()
            ),
        )
        previous_snapshot_node: str | None = None
        for snapshot in snapshots:
            snapshot_node = add_node(
                "governance",
                f"trust-snapshot:{snapshot.id}",
                f"snapshot:{snapshot.id}",
                {
                    "created_at": _iso(snapshot.created_at),
                    "immutable_hash": snapshot.immutable_hash,
                    "previous_snapshot_hash": (snapshot.snapshot_data or {}).get("snapshot", {}).get("previous_snapshot_hash"),
                },
            )
            if previous_snapshot_node is not None:
                add_edge(previous_snapshot_node, snapshot_node, "lineage", {"scope": "trust_snapshot"})
            previous_snapshot_node = snapshot_node

        nodes = list(node_index.values())
        return self._finalize_graph(nodes, edges, tenant_id=tenant_id)

    def _finalize_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        unique_nodes = {node["id"]: node for node in nodes}
        unique_edges = {(edge["source"], edge["target"], edge["type"], edge["hash"]): edge for edge in edges}
        sorted_nodes = [unique_nodes[key] for key in sorted(unique_nodes)]
        sorted_edges = [unique_edges[key] for key in sorted(unique_edges)]

        incoming: dict[str, list[str]] = defaultdict(list)
        outgoing: dict[str, list[str]] = defaultdict(list)
        for edge in sorted_edges:
            incoming[edge["target"]].append(edge["hash"])
            outgoing[edge["source"]].append(edge["hash"])

        for node in sorted_nodes:
            node["incoming_merkle_root"] = _merkle_root(incoming.get(node["id"], []))
            node["outgoing_merkle_root"] = _merkle_root(outgoing.get(node["id"], []))
            node["lineage_hash"] = _sha256(
                {
                    "hash": node["hash"],
                    "incoming_merkle_root": node["incoming_merkle_root"],
                    "outgoing_merkle_root": node["outgoing_merkle_root"],
                }
            )

        node_hashes = [node["lineage_hash"] for node in sorted_nodes]
        edge_hashes = [edge["hash"] for edge in sorted_edges]
        counts = Counter(node["type"] for node in sorted_nodes)
        edge_counts = Counter(edge["type"] for edge in sorted_edges)

        return {
            "deterministic": True,
            "generated_at": datetime.now(UTC).isoformat(),
            "graph_hash": _sha256({"nodes": node_hashes, "edges": edge_hashes}),
            "merkle_root": _merkle_root(node_hashes + edge_hashes),
            "nodes": sorted_nodes,
            "edges": sorted_edges,
            "offline_capable": True,
            "replay_reproducible": True,
            "summary": {
                "edge_count": len(sorted_edges),
                "edge_types": dict(edge_counts),
                "node_count": len(sorted_nodes),
                "node_types": dict(counts),
                "tenant_id": tenant_id,
            },
            "tenant_id": tenant_id,
        }

    async def get_full_graph(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        *,
        include_manual: bool = True,
        redact_sovereign: bool = True,
    ) -> dict[str, Any]:
        derived = await self._build_derived_graph(db, tenant_id=tenant_id, redact_sovereign=redact_sovereign)
        if not include_manual:
            return derived
        manual = await self._load_manual_graph(db)
        return self._finalize_graph(
            manual["nodes"] + derived["nodes"],
            manual["edges"] + derived["edges"],
            tenant_id=tenant_id,
        )

    async def get_node_lineage(
        self,
        db: AsyncSession,
        *,
        node_id: str,
        tenant_id: str | None = None,
        depth: int = 3,
    ) -> dict[str, Any]:
        graph = await self.get_full_graph(db, tenant_id=tenant_id)
        nodes = {node["id"]: node for node in graph["nodes"]}
        if node_id not in nodes:
            for node in graph["nodes"]:
                if str(node.get("external_id")) == str(node_id):
                    node_id = node["id"]
                    break
        if node_id not in nodes:
            return {"node_id": node_id, "found": False, "nodes": [], "edges": []}

        selected_nodes = {node_id}
        selected_edges: list[dict[str, Any]] = []
        frontier = {node_id}
        remaining = max(depth, 1)
        while frontier and remaining > 0:
            next_frontier: set[str] = set()
            for edge in graph["edges"]:
                if edge["source"] in frontier or edge["target"] in frontier:
                    selected_edges.append(edge)
                    next_frontier.add(edge["source"])
                    next_frontier.add(edge["target"])
            next_frontier -= selected_nodes
            selected_nodes.update(next_frontier)
            frontier = next_frontier
            remaining -= 1
        return {
            "node_id": node_id,
            "found": True,
            "nodes": [nodes[item] for item in sorted(selected_nodes)],
            "edges": sorted(selected_edges, key=lambda item: (item["type"], item["source"], item["target"])),
        }

    async def verify_graph_integrity(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []

        manual = await self._load_manual_graph(db)
        for node in manual["nodes"]:
            expected_hash = self.calculate_node_hash(
                node["type"],
                node["label"],
                node["metadata"],
                node.get("external_id"),
            )
            if node["hash"] != expected_hash:
                violations.append(
                    {
                        "type": "node_hash_mismatch",
                        "id": node["id"],
                        "expected": expected_hash,
                        "actual": node["hash"],
                    }
                )
        for edge in manual["edges"]:
            expected_hash = self.calculate_edge_hash(edge["source"], edge["target"], edge["type"], edge["metadata"])
            if edge["hash"] != expected_hash:
                violations.append(
                    {
                        "type": "edge_hash_mismatch",
                        "id": edge["id"],
                        "expected": expected_hash,
                        "actual": edge["hash"],
                    }
                )

        graph = await self.get_full_graph(db, tenant_id=tenant_id)
        node_ids = {node["id"] for node in graph["nodes"]}
        seen_ids: set[str] = set()
        for node in graph["nodes"]:
            if node["id"] in seen_ids:
                violations.append(
                    {
                        "type": "duplicate_node_id",
                        "id": node["id"],
                        "expected": "unique",
                        "actual": node["id"],
                    }
                )
            seen_ids.add(node["id"])
        for edge in graph["edges"]:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                violations.append(
                    {
                        "type": "edge_reference_missing",
                        "id": edge["id"],
                        "expected": "existing_nodes",
                        "actual": f"{edge['source']}->{edge['target']}",
                    }
                )

        return violations
