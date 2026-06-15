from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.commercial.commercial_operations_center import CommercialCryptographicTrustSnapshot
from app.models.commercial.commercial_trust_violation import CommercialTrustViolation
from app.models.commercial.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowStage,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .cryptographic_topology import CryptographicTopologyService
from .trust_graph import TrustGraphService


def _sha256(payload: Any) -> str:
    if not isinstance(payload, str):
        payload = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TrustViolationDetectionService:
    def __init__(self) -> None:
        self.trust_graph_service = TrustGraphService()
        self.topology_service = CryptographicTopologyService()

    async def _safe_scalars(self, db: AsyncSession, statement) -> list[Any]:
        try:
            return (await db.execute(statement)).scalars().all()
        except SQLAlchemyError:
            return []

    async def _scan_graph(
        self, db: AsyncSession, *, tenant_id: str | None = None
    ) -> list[dict[str, Any]]:
        issues = await self.trust_graph_service.verify_graph_integrity(db, tenant_id=tenant_id)
        graph = await self.trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
        node_map = {node["id"]: node for node in graph["nodes"]}

        for edge in graph["edges"]:
            source = node_map.get(edge["source"])
            target = node_map.get(edge["target"])
            if source is None or target is None:
                continue
            source_tenant = (source["metadata"] or {}).get("tenant_id") or (
                source["metadata"] or {}
            ).get("client_id")
            target_tenant = (target["metadata"] or {}).get("tenant_id") or (
                target["metadata"] or {}
            ).get("client_id")
            if source_tenant and target_tenant and str(source_tenant) != str(target_tenant):
                if edge["type"] not in {"federation_mapping", "sovereign_isolation"}:
                    issues.append(
                        {
                            "type": "tenant_isolation_violation",
                            "id": edge["id"],
                            "expected": str(source_tenant),
                            "actual": str(target_tenant),
                            "details": {"source": source["id"], "target": target["id"]},
                        }
                    )

        workflow_rows = await self._safe_scalars(
            db,
            select(CommercialWorkflowExecution).order_by(
                CommercialWorkflowExecution.started_at.asc()
            ),
        )
        execution_ids = {str(row.id) for row in workflow_rows}
        for row in workflow_rows:
            if tenant_id is not None and row.tenant_id not in {None, tenant_id}:
                continue
            if (
                row.replay_of_execution_id is not None
                and str(row.replay_of_execution_id) not in execution_ids
            ):
                issues.append(
                    {
                        "type": "replay_lineage_break",
                        "id": str(row.id),
                        "expected": str(row.replay_of_execution_id),
                        "actual": "missing_replay_parent",
                    }
                )

        stage_rows = await self._safe_scalars(
            db,
            select(CommercialWorkflowStage).order_by(
                CommercialWorkflowStage.execution_id.asc(),
                CommercialWorkflowStage.stage_order.asc(),
            ),
        )
        stages_by_execution: dict[str, set[str]] = {}
        for stage in stage_rows:
            if tenant_id is not None and stage.tenant_id not in {None, tenant_id}:
                continue
            stages_by_execution.setdefault(str(stage.execution_id), set()).add(stage.stage_key)
        for stage in stage_rows:
            if tenant_id is not None and stage.tenant_id not in {None, tenant_id}:
                continue
            available = stages_by_execution.get(str(stage.execution_id), set())
            for dependency in stage.dependencies_json or []:
                if dependency not in available:
                    issues.append(
                        {
                            "type": "dependency_integrity_failure",
                            "id": str(stage.id),
                            "expected": dependency,
                            "actual": "missing_stage_dependency",
                        }
                    )

        snapshots = await self._safe_scalars(
            db,
            select(CommercialCryptographicTrustSnapshot).order_by(
                CommercialCryptographicTrustSnapshot.created_at.asc()
            ),
        )
        previous_hash: str | None = None
        for snapshot in snapshots:
            current_hash = _sha256(snapshot.snapshot_data)
            if current_hash != snapshot.immutable_hash:
                issues.append(
                    {
                        "type": "snapshot_hash_mismatch",
                        "id": str(snapshot.id),
                        "expected": current_hash,
                        "actual": snapshot.immutable_hash,
                    }
                )
            linked_hash = (
                (snapshot.snapshot_data or {}).get("snapshot", {}).get("previous_snapshot_hash")
            )
            if previous_hash is not None and linked_hash != previous_hash:
                issues.append(
                    {
                        "type": "snapshot_chain_break",
                        "id": str(snapshot.id),
                        "expected": previous_hash,
                        "actual": linked_hash,
                    }
                )
            previous_hash = snapshot.immutable_hash

        return issues

    async def run_detection(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
        persist: bool = True,
    ) -> list[CommercialTrustViolation]:
        issues = await self._scan_graph(db, tenant_id=tenant_id)
        detected: list[CommercialTrustViolation] = []

        for issue in issues:
            violation_type = issue["type"]
            severity = "critical"
            if violation_type in {
                "tenant_isolation_violation",
                "snapshot_chain_break",
                "replay_lineage_break",
            }:
                severity = "high"
            elif violation_type in {"dependency_integrity_failure", "edge_reference_missing"}:
                severity = "medium"

            evidence_hash = issue.get("actual") or _sha256(issue)
            existing = (
                await db.execute(
                    select(CommercialTrustViolation).where(
                        CommercialTrustViolation.violation_type == violation_type,
                        CommercialTrustViolation.evidence_hash == evidence_hash,
                        CommercialTrustViolation.remediation_status == "pending",
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                detected.append(existing)
                continue
            violation = CommercialTrustViolation(
                violation_type=violation_type,
                severity=severity,
                details_json=issue,
                evidence_hash=evidence_hash,
            )
            db.add(violation)
            detected.append(violation)

        if persist and detected:
            await db.commit()
            for item in detected:
                await db.refresh(item)
        elif not persist:
            await db.flush()

        return detected

    async def get_active_violations(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> list[CommercialTrustViolation]:
        rows = await self._safe_scalars(
            db,
            select(CommercialTrustViolation).where(
                CommercialTrustViolation.remediation_status == "pending"
            ),
        )
        if tenant_id is None:
            return rows
        filtered: list[CommercialTrustViolation] = []
        for row in rows:
            details = row.details_json or {}
            detail_tenant = details.get("tenant_id") or details.get("details", {}).get("tenant_id")
            if detail_tenant in {None, tenant_id}:
                filtered.append(row)
        return filtered

    async def summarize_integrity(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        issues = await self._scan_graph(db, tenant_id=tenant_id)
        topology_ok = await self.topology_service.verify_topology_integrity(db, tenant_id=tenant_id)
        timeline = await self.topology_service.build_runtime_integrity_timeline(db)
        return {
            "status": "healthy" if not issues and topology_ok else "compromised",
            "tenant_id": tenant_id,
            "topology_ok": topology_ok,
            "violation_count": len(issues),
            "violations": issues,
            "timeline": timeline,
        }
