from __future__ import annotations

from typing import Any

from app.models.commercial.commercial_federated_workflows import (
    CommercialFederatedWorkflowExecution,
    CommercialWorkflowReplayFederationReport,
)
from app.models.commercial.commercial_sovereign_governance import CommercialOfflineRevocationList
from app.models.commercial.commercial_workflows import CommercialWorkflowExecution, CommercialWorkflowStage
from app.services.workflows.federated_execution import sign_federated_payload
from app.services.workflows.workflow_provenance import (
    canonical_json,
    redact_sensitive_payload,
    sha256_hex,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class FederatedWorkflowReplayService:
    async def _federated_execution(self, db: AsyncSession, federated_execution_id) -> CommercialFederatedWorkflowExecution:
        row = await db.get(CommercialFederatedWorkflowExecution, federated_execution_id)
        if row is None:
            raise ValueError("federated_workflow_execution_not_found")
        return row

    async def _workflow_execution(self, db: AsyncSession, execution_id) -> CommercialWorkflowExecution:
        row = await db.get(CommercialWorkflowExecution, execution_id)
        if row is None:
            raise ValueError("workflow_execution_not_found")
        return row

    async def _stages(self, db: AsyncSession, execution_id) -> list[CommercialWorkflowStage]:
        return (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution_id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        ).scalars().all()

    async def _latest_report(self, db: AsyncSession, federated_execution_id) -> CommercialWorkflowReplayFederationReport | None:
        return (
            await db.execute(
                select(CommercialWorkflowReplayFederationReport)
                .where(CommercialWorkflowReplayFederationReport.federated_execution_id == federated_execution_id)
                .order_by(desc(CommercialWorkflowReplayFederationReport.created_at), desc(CommercialWorkflowReplayFederationReport.id))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _is_peer_revoked(self, db: AsyncSession, peer_cluster_id: str | None) -> bool:
        if not peer_cluster_id:
            return False
        crls = (
            await db.execute(
                select(CommercialOfflineRevocationList).order_by(CommercialOfflineRevocationList.created_at.desc())
            )
        ).scalars().all()
        return any(peer_cluster_id in (crl.revoked_peer_ids_json or []) for crl in crls)

    async def validate_replay(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        replay_execution_id=None,
    ) -> CommercialWorkflowReplayFederationReport:
        federated = await self._federated_execution(db, federated_execution_id)
        source = await self._workflow_execution(db, federated.workflow_execution_id)
        replay = await self._workflow_execution(db, replay_execution_id or federated.workflow_execution_id)
        source_stages = await self._stages(db, source.id)
        replay_stages = await self._stages(db, replay.id)
        stage_pairs = list(zip(source_stages, replay_stages, strict=False))
        mismatches: list[dict[str, Any]] = []
        total = max(len(source_stages), len(replay_stages), 1)
        for index, pair in enumerate(stage_pairs):
            if len(pair) != 2:
                mismatches.append({"stage_index": index, "reason": "stage_count_mismatch"})
                continue
            left, right = pair
            if left.stage_hash != right.stage_hash or left.runtime_snapshot_hash != right.runtime_snapshot_hash:
                mismatches.append(
                    {
                        "stage_index": index,
                        "stage_key": left.stage_key,
                        "source_stage_hash": left.stage_hash,
                        "replay_stage_hash": right.stage_hash,
                        "source_runtime_snapshot_hash": left.runtime_snapshot_hash,
                        "replay_runtime_snapshot_hash": right.runtime_snapshot_hash,
                    }
                )
        if len(source_stages) != len(replay_stages):
            mismatches.append(
                {
                    "stage_index": min(len(source_stages), len(replay_stages)),
                    "reason": "stage_count_mismatch",
                    "source_count": len(source_stages),
                    "replay_count": len(replay_stages),
                }
            )
        mismatch_detected = bool(mismatches) or any(
            [
                source.execution_hash_chain != replay.execution_hash_chain,
                source.dag_hash != replay.dag_hash,
            ]
        )
        drift_score = round(len(mismatches) / total, 4)
        previous = await self._latest_report(db, federated_execution_id)
        payload = {
            "federated_execution_id": str(federated.id),
            "source_execution_id": str(source.id),
            "replay_execution_id": str(replay.id),
            "deterministic_clock": federated.deterministic_clock,
            "mismatch_detected": mismatch_detected,
            "drift_score": drift_score,
            "mismatches": mismatches,
            "deterministic_ordering": [stage.stage_key for stage in source_stages],
            "runtime_snapshot_hashes": [stage.runtime_snapshot_hash for stage in replay_stages],
            "routing_decision_hash": federated.routing_decision_hash,
        }
        report = CommercialWorkflowReplayFederationReport(
            federated_execution_id=federated.id,
            source_execution_id=source.id,
            workflow_id=federated.workflow_id,
            tenant_id=federated.tenant_id,
            client_id=federated.client_id,
            region_id=federated.region_id,
            cluster_id=federated.cluster_id,
            execution_hash=federated.execution_hash,
            dag_hash=federated.dag_hash,
            provenance_hash=federated.provenance_hash,
            lease_owner=federated.lease_owner,
            consensus_status=federated.consensus_status,
            replay_status="mismatch_detected" if mismatch_detected else "verified",
            federation_mode=federated.federation_mode,
            deterministic_clock=federated.deterministic_clock,
            previous_hash=previous.immutable_hash if previous else federated.immutable_hash,
            signed_execution_receipt=federated.signed_execution_receipt,
            attestation_summary=federated.attestation_summary,
            sovereign_mode=federated.sovereign_mode,
            drift_score=drift_score,
            mismatch_detected=mismatch_detected,
            replay_report_json=payload,
            report_bundle_json=None,
        )
        report.immutable_hash = sha256_hex(
            {
                "federated_execution_id": str(federated.id),
                "replay_status": report.replay_status,
                "drift_score": drift_score,
                "previous_hash": report.previous_hash,
                "payload": payload,
            }
        )
        report.report_signature = sign_federated_payload(payload, scope="federated_replay_report")
        db.add(report)
        federated.replay_status = report.replay_status
        federated.drift_detected = mismatch_detected
        await db.flush()
        return report

    async def export_signed_bundle(
        self,
        db: AsyncSession,
        *,
        report_id,
        media_label: str = "offline-media",
    ) -> dict[str, Any]:
        report = await db.get(CommercialWorkflowReplayFederationReport, report_id)
        if report is None:
            raise ValueError("federated_replay_report_not_found")
        if report.sovereign_mode == "sovereign_airgap" and await self._is_peer_revoked(db, report.cluster_id):
            raise ValueError("peer_revoked_by_offline_crl")
        manifest = {
            "report_id": str(report.id),
            "workflow_id": report.workflow_id,
            "cluster_id": report.cluster_id,
            "region_id": report.region_id,
            "media_label": media_label,
            "sovereign_mode": report.sovereign_mode,
            "report_hash": report.immutable_hash,
        }
        payload = {
            "manifest": manifest,
            "report": redact_sensitive_payload(report.replay_report_json or {}),
        }
        bundle = {
            "manifest": manifest,
            "payload": payload,
            "payload_hash": sha256_hex(payload),
            "signature": sign_federated_payload(payload, scope="federated_replay_bundle"),
        }
        report.report_bundle_json = bundle
        await db.flush()
        return bundle

    async def verify_offline_bundle(
        self,
        db: AsyncSession,
        *,
        bundle: dict[str, Any],
    ) -> dict[str, Any]:
        manifest = bundle.get("manifest") or {}
        payload = bundle.get("payload") or {}
        signature = bundle.get("signature")
        payload_hash = bundle.get("payload_hash")
        cluster_id = manifest.get("cluster_id")
        if await self._is_peer_revoked(db, cluster_id):
            return {"valid": False, "reason": "peer_revoked_by_offline_crl"}
        expected_hash = sha256_hex(payload)
        expected_signature = sign_federated_payload(payload, scope="federated_replay_bundle")
        valid = payload_hash == expected_hash and signature == expected_signature
        return {
            "valid": valid,
            "reason": None if valid else "bundle_signature_mismatch",
            "bundle_hash": sha256_hex(canonical_json(bundle)),
        }
