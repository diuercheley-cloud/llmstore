from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_db
from app.services.security.cryptographic_topology import CryptographicTopologyService
from app.services.security.trust_graph import TrustGraphService
from app.services.security.trust_snapshotting import TrustSnapshottingService
from app.services.security.trust_violation_detection import TrustViolationDetectionService

router = APIRouter(tags=["commercial_operations_center"])

trust_graph_service = TrustGraphService()
snapshot_service = TrustSnapshottingService()
violation_service = TrustViolationDetectionService()
topology_service = CryptographicTopologyService()


@router.get("/graph")
async def get_trust_graph(
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    return await trust_graph_service.get_full_graph(db, tenant_id=tenant_id)


@router.post("/snapshot")
async def create_trust_snapshot(
    tenant_id: str | None = Query(default=None),
    format: str = Query(default="record", pattern="^(record|json|signed_bundle|offline_audit_package)$"),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    snapshot = await snapshot_service.create_snapshot(db, tenant_id=tenant_id)
    if format == "record":
        return {
            "created_at": snapshot.created_at.isoformat(),
            "id": str(snapshot.id),
            "immutable_hash": snapshot.immutable_hash,
        }
    return await snapshot_service.export_snapshot_bundle(
        db,
        snapshot=snapshot,
        format=format,
        tenant_id=tenant_id,
    )


@router.get("/trust-violations")
async def get_trust_violations(
    tenant_id: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    if refresh:
        await violation_service.run_detection(db, tenant_id=tenant_id, persist=True)
    violations = await violation_service.get_active_violations(db, tenant_id=tenant_id)
    return [
        {
            "detected_at": item.detected_at.isoformat(),
            "details": item.details_json,
            "evidence_hash": item.evidence_hash,
            "id": str(item.id),
            "severity": item.severity,
            "type": item.violation_type,
        }
        for item in violations
    ]


@router.get("/lineage")
async def get_node_lineage(
    node_id: str,
    tenant_id: str | None = Query(default=None),
    depth: int = Query(default=3, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    return await topology_service.compute_node_lineage(
        db,
        node_id=node_id,
        tenant_id=tenant_id,
        depth=depth,
    )


@router.get("/integrity")
async def get_system_integrity(
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    summary = await violation_service.summarize_integrity(db, tenant_id=tenant_id)
    graph = await trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
    sovereign = await topology_service.build_sovereign_isolation_graph(db, tenant_id=tenant_id)
    replay = await topology_service.replay_lineage_tracking(db, tenant_id=tenant_id)
    return {
        **summary,
        "graph_hash": graph["graph_hash"],
        "merkle_root": graph["merkle_root"],
        "replay_lineage": replay,
        "sovereign_isolation": sovereign,
    }


@router.get("/federation-map")
async def get_federation_map(
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    return await topology_service.map_federation_trust(db, tenant_id=tenant_id)
