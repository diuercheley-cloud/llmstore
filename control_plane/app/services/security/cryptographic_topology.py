from __future__ import annotations

from collections import Counter
from typing import Any

from app.models.commercial.commercial_model_supply_chain import CommercialModelIntegrityScan
from app.models.commercial.commercial_runtime_fabric import CommercialRuntimeFabricEvent
from app.models.commercial.commercial_sovereign_governance import (
    CommercialHardwareAttestationRecord,
)
from app.models.commercial.commercial_workflows import CommercialWorkflowExecution
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .trust_graph import TrustGraphService


class CryptographicTopologyService:
    def __init__(self) -> None:
        self.trust_graph_service = TrustGraphService()

    async def _safe_scalars(self, db: AsyncSession, statement) -> list[Any]:
        try:
            return (await db.execute(statement)).scalars().all()
        except SQLAlchemyError:
            return []

    async def propagate_trust(
        self,
        db: AsyncSession,
        source_node_id: str,
        target_node_id: str,
        context: dict[str, Any],
    ):
        payload = {
            "context": context,
            "propagation_mode": "runtime_trust_propagation",
            "verifiable": True,
        }
        return await self.trust_graph_service.add_edge(
            db,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type="runtime_trust_propagation",
            metadata=payload,
        )

    async def merkle_linked_topology(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        graph = await self.trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
        node_roots = [node["lineage_hash"] for node in graph["nodes"]]
        edge_roots = [edge["hash"] for edge in graph["edges"]]
        return {
            "graph_hash": graph["graph_hash"],
            "merkle_root": graph["merkle_root"],
            "node_lineage_root": self.trust_graph_service.calculate_node_hash(
                "topology",
                "node_lineage_root",
                {"roots": node_roots},
                external_id=tenant_id or "global",
            ),
            "edge_lineage_root": self.trust_graph_service.calculate_node_hash(
                "topology",
                "edge_lineage_root",
                {"roots": edge_roots},
                external_id=tenant_id or "global",
            ),
            "summary": graph["summary"],
        }

    async def compute_node_lineage(
        self,
        db: AsyncSession,
        *,
        node_id: str,
        tenant_id: str | None = None,
        depth: int = 3,
    ) -> dict[str, Any]:
        lineage = await self.trust_graph_service.get_node_lineage(
            db,
            node_id=node_id,
            tenant_id=tenant_id,
            depth=depth,
        )
        if not lineage.get("found"):
            return lineage
        lineage["topology_hash"] = self.trust_graph_service.calculate_node_hash(
            "lineage",
            node_id,
            {
                "edge_count": len(lineage["edges"]),
                "node_count": len(lineage["nodes"]),
            },
            external_id=node_id,
        )
        return lineage

    async def map_federation_trust(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        graph = await self.trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
        federation_nodes = [node for node in graph["nodes"] if node["type"] == "federation"]
        federation_edges = [
            edge for edge in graph["edges"] if edge["type"] in {"federation_mapping", "audit_event"}
        ]
        trust_levels = Counter(
            (node["metadata"] or {}).get("trust_level", "unknown") for node in federation_nodes
        )
        return {
            "nodes": federation_nodes,
            "edges": federation_edges,
            "consistency": {
                "peer_count": len(federation_nodes),
                "trust_levels": dict(trust_levels),
                "mapping_count": len(
                    [edge for edge in federation_edges if edge["type"] == "federation_mapping"]
                ),
            },
        }

    async def build_runtime_integrity_timeline(
        self,
        db: AsyncSession,
        *,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        runtime_events = await self._safe_scalars(
            db,
            select(CommercialRuntimeFabricEvent)
            .order_by(CommercialRuntimeFabricEvent.created_at.desc())
            .limit(limit),
        )
        integrity_scans = await self._safe_scalars(
            db,
            select(CommercialModelIntegrityScan)
            .order_by(CommercialModelIntegrityScan.created_at.desc())
            .limit(limit),
        )
        hardware = await self._safe_scalars(
            db,
            select(CommercialHardwareAttestationRecord)
            .order_by(CommercialHardwareAttestationRecord.created_at.desc())
            .limit(limit),
        )

        timeline: list[dict[str, Any]] = []
        for item in runtime_events:
            timeline.append(
                {
                    "kind": "runtime_event",
                    "timestamp": item.created_at.isoformat(),
                    "subject": item.source_node_id,
                    "status": item.severity,
                    "summary": item.event_type,
                }
            )
        for item in integrity_scans:
            timeline.append(
                {
                    "kind": "model_integrity_scan",
                    "timestamp": item.created_at.isoformat(),
                    "subject": item.model_name,
                    "status": item.integrity_status,
                    "summary": item.scan_type,
                }
            )
        for item in hardware:
            timeline.append(
                {
                    "kind": "hardware_attestation",
                    "timestamp": item.created_at.isoformat(),
                    "subject": item.node_id or item.cluster_id,
                    "status": item.status,
                    "summary": item.attestation_type,
                }
            )
        timeline.sort(key=lambda item: item["timestamp"], reverse=True)
        return timeline[:limit]

    async def build_sovereign_isolation_graph(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        graph = await self.trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
        nodes = [
            node
            for node in graph["nodes"]
            if node["type"] in {"sovereign", "confidential", "runtime"}
        ]
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge
            for edge in graph["edges"]
            if edge["source"] in node_ids and edge["target"] in node_ids
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "merkle_root": graph["merkle_root"],
        }

    async def replay_lineage_tracking(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(CommercialWorkflowExecution).order_by(
            CommercialWorkflowExecution.started_at.desc()
        )
        rows = await self._safe_scalars(db, query)
        lineage: list[dict[str, Any]] = []
        for row in rows:
            if tenant_id is not None and row.tenant_id not in {None, tenant_id}:
                continue
            lineage.append(
                {
                    "execution_id": str(row.id),
                    "replay_of_execution_id": str(row.replay_of_execution_id)
                    if row.replay_of_execution_id
                    else None,
                    "replay_status": row.replay_status,
                    "status": row.status,
                    "tenant_id": row.tenant_id,
                }
            )
        return lineage

    async def verify_topology_integrity(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> bool:
        violations = await self.trust_graph_service.verify_graph_integrity(db, tenant_id=tenant_id)
        return len(violations) == 0
