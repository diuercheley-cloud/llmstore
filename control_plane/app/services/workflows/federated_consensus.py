from __future__ import annotations

import math
from collections import Counter
from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_federated_workflows import (
    CommercialFederatedWorkflowExecution,
    CommercialWorkflowConsensusEvent,
    CommercialWorkflowExecutionPeer,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.federated_execution import sign_federated_payload
from app.services.workflows.workflow_provenance import redact_sensitive_payload, sha256_hex
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class FederatedWorkflowConsensusService:
    async def _execution(self, db: AsyncSession, federated_execution_id) -> CommercialFederatedWorkflowExecution:
        row = await db.get(CommercialFederatedWorkflowExecution, federated_execution_id)
        if row is None:
            raise ValueError("federated_workflow_execution_not_found")
        return row

    async def _peers(self, db: AsyncSession, federated_execution_id) -> list[CommercialWorkflowExecutionPeer]:
        return (
            await db.execute(
                select(CommercialWorkflowExecutionPeer)
                .where(CommercialWorkflowExecutionPeer.federated_execution_id == federated_execution_id)
                .order_by(CommercialWorkflowExecutionPeer.created_at.asc())
            )
        ).scalars().all()

    async def _latest_event(self, db: AsyncSession, federated_execution_id) -> CommercialWorkflowConsensusEvent | None:
        return (
            await db.execute(
                select(CommercialWorkflowConsensusEvent)
                .where(CommercialWorkflowConsensusEvent.federated_execution_id == federated_execution_id)
                .order_by(desc(CommercialWorkflowConsensusEvent.created_at), desc(CommercialWorkflowConsensusEvent.id))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def append_event(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        event_type: str,
        peer_id=None,
        consensus_status: str,
        quorum_size: int,
        quorum_threshold: int,
        event_payload: dict[str, Any] | None = None,
    ) -> CommercialWorkflowConsensusEvent:
        execution = await self._execution(db, federated_execution_id)
        previous = await self._latest_event(db, federated_execution_id)
        sanitized_payload = sanitize_report_payload(redact_sensitive_payload(event_payload or {}))
        row = CommercialWorkflowConsensusEvent(
            federated_execution_id=execution.id,
            peer_id=peer_id,
            workflow_id=execution.workflow_id,
            tenant_id=execution.tenant_id,
            client_id=execution.client_id,
            region_id=execution.region_id,
            cluster_id=execution.cluster_id,
            event_type=event_type,
            execution_hash=execution.execution_hash,
            dag_hash=execution.dag_hash,
            provenance_hash=execution.provenance_hash,
            lease_owner=execution.lease_owner,
            consensus_status=consensus_status,
            replay_status=execution.replay_status,
            federation_mode=execution.federation_mode,
            deterministic_clock=execution.deterministic_clock,
            previous_hash=previous.immutable_hash if previous else execution.immutable_hash,
            signed_execution_receipt=sign_federated_payload(sanitized_payload, scope=f"consensus:{event_type}"),
            attestation_summary=execution.attestation_summary,
            sovereign_mode=execution.sovereign_mode,
            quorum_size=quorum_size,
            quorum_threshold=quorum_threshold,
            event_payload_json=sanitized_payload,
            created_at=utc_now(),
        )
        row.immutable_hash = sha256_hex(
            {
                "federated_execution_id": str(execution.id),
                "event_type": event_type,
                "consensus_status": consensus_status,
                "quorum_size": quorum_size,
                "quorum_threshold": quorum_threshold,
                "previous_hash": row.previous_hash,
                "payload": sanitized_payload,
            }
        )
        db.add(row)
        execution.consensus_status = consensus_status
        await db.flush()
        return row

    async def validate_consensus(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        quorum_threshold: int | None = None,
    ) -> dict[str, Any]:
        execution = await self._execution(db, federated_execution_id)
        peers = await self._peers(db, federated_execution_id)
        trusted = [peer for peer in peers if peer.trust_status == "trusted"]
        peer_hashes = [peer.execution_hash for peer in trusted if peer.execution_hash]
        counter = Counter([execution.execution_hash, *peer_hashes])
        canonical_hash, canonical_votes = counter.most_common(1)[0] if counter else (execution.execution_hash, 1)
        quorum_size = 1 + len(trusted)
        threshold = quorum_threshold or max(1, math.floor(quorum_size / 2) + 1)
        mismatches = [
            {
                "peer_cluster_id": peer.peer_cluster_id,
                "peer_hash": peer.execution_hash,
                "expected_hash": execution.execution_hash,
            }
            for peer in trusted
            if peer.execution_hash and peer.execution_hash != canonical_hash
        ]
        status = "verified" if canonical_votes >= threshold and not mismatches else "mismatch_detected"
        if canonical_votes < threshold:
            status = "quorum_failed"
        execution.consensus_status = status
        execution.reconciliation_status = "reconciliation_required" if status != "verified" else "verified"
        execution.drift_detected = status != "verified"
        await self.append_event(
            db,
            federated_execution_id=federated_execution_id,
            event_type="quorum_validated" if status == "verified" else "quorum_failed",
            consensus_status=status,
            quorum_size=quorum_size,
            quorum_threshold=threshold,
            event_payload={
                "canonical_hash": canonical_hash,
                "canonical_votes": canonical_votes,
                "mismatches": mismatches,
            },
        )
        return {
            "federated_execution_id": str(execution.id),
            "consensus_status": status,
            "quorum_size": quorum_size,
            "quorum_threshold": threshold,
            "canonical_hash": canonical_hash,
            "mismatches": mismatches,
        }

    async def reconcile_execution(self, db: AsyncSession, *, federated_execution_id) -> dict[str, Any]:
        execution = await self._execution(db, federated_execution_id)
        validation = await self.validate_consensus(db, federated_execution_id=federated_execution_id)
        if validation["consensus_status"] != "verified":
            execution.execution_hash = validation["canonical_hash"]
            execution.consensus_status = "reconciled"
            execution.reconciliation_status = "auto_reconciled"
            execution.drift_detected = False
            await self.append_event(
                db,
                federated_execution_id=federated_execution_id,
                event_type="reconciled",
                consensus_status="reconciled",
                quorum_size=validation["quorum_size"],
                quorum_threshold=validation["quorum_threshold"],
                event_payload={"canonical_hash": validation["canonical_hash"]},
            )
            validation["consensus_status"] = "reconciled"
        await db.flush()
        return validation
