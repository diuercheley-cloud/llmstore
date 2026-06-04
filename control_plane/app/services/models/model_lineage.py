from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.commercial_model_lifecycle import CommercialModelLineage
from app.services.models.model_lifecycle_manager import _log_audit, _sanitize_text
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

DERIVATION_METHODS = {
    "original_import",
    "offline_promotion",
    "version_upgrade",
    "finetune_derivative",
    "quantization_derivative",
    "merge_derivative",
    "conversion_derivative",
    "rollback_restoration",
}


async def create_lineage_entry(
    db: AsyncSession,
    *,
    lifecycle_record_id: UUID,
    parent_lineage_id: UUID | None = None,
    source_type: str,
    source_ref: str | None = None,
    source_cluster_id: str | None = None,
    derivation_method: str,
    artifact_hash: str,
    predecessor_hash: str | None = None,
    provenance_id: UUID | None = None,
    evidence_json: dict[str, Any] | None = None,
) -> CommercialModelLineage:
    if derivation_method not in DERIVATION_METHODS:
        raise ValueError(f"Invalid derivation method: {derivation_method}")
    depth = 0
    if parent_lineage_id:
        parent = await db.get(CommercialModelLineage, parent_lineage_id)
        if parent:
            depth = parent.depth + 1
    dag_node = {
        "id": None,
        "parent_id": str(parent_lineage_id) if parent_lineage_id else None,
        "source_type": source_type,
        "derivation_method": derivation_method,
        "artifact_hash": artifact_hash,
        "predecessor_hash": predecessor_hash,
        "depth": depth,
    }
    entry = CommercialModelLineage(
        lifecycle_record_id=lifecycle_record_id,
        parent_lineage_id=parent_lineage_id,
        source_type=source_type,
        source_ref=_sanitize_text(source_ref, max_length=512),
        source_cluster_id=_sanitize_text(source_cluster_id, max_length=255),
        derivation_method=derivation_method,
        artifact_hash=artifact_hash,
        predecessor_hash=predecessor_hash,
        depth=depth,
        provenance_id=provenance_id,
        evidence_json=sanitize_report_payload(evidence_json) if evidence_json else None,
        dag_node_json=dag_node,
    )
    db.add(entry)
    await db.flush()
    dag_node["id"] = str(entry.id)
    entry.dag_node_json = dag_node
    await db.flush()
    await _log_audit(
        db,
        action="lineage_entry_created",
        status="success",
        payload={"lifecycle_record_id": str(lifecycle_record_id), "derivation_method": derivation_method},
        result={"lineage_id": str(entry.id), "depth": depth},
    )
    return entry


async def get_lineage_dag(
    db: AsyncSession,
    lifecycle_record_id: UUID,
) -> dict[str, Any]:
    result = await db.execute(
        select(CommercialModelLineage)
        .where(CommercialModelLineage.lifecycle_record_id == lifecycle_record_id)
        .order_by(CommercialModelLineage.depth.asc(), CommercialModelLineage.created_at.asc())
    )
    entries = result.scalars().all()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for entry in entries:
        node = {
            "id": str(entry.id),
            "source_type": entry.source_type,
            "derivation_method": entry.derivation_method,
            "artifact_hash": entry.artifact_hash,
            "predecessor_hash": entry.predecessor_hash,
            "depth": entry.depth,
            "source_cluster_id": entry.source_cluster_id,
            "created_at": entry.created_at.isoformat(),
        }
        nodes.append(node)
        if entry.parent_lineage_id:
            edges.append({"from": str(entry.parent_lineage_id), "to": str(entry.id)})
    return {
        "lifecycle_record_id": str(lifecycle_record_id),
        "nodes": nodes,
        "edges": edges,
        "depth": max((e.depth for e in entries), default=-1),
        "total_entries": len(entries),
    }


async def validate_lineage(
    db: AsyncSession,
    lifecycle_record_id: UUID,
) -> dict[str, Any]:
    result = await db.execute(
        select(CommercialModelLineage)
        .where(CommercialModelLineage.lifecycle_record_id == lifecycle_record_id)
        .order_by(CommercialModelLineage.depth.asc())
    )
    entries = result.scalars().all()
    if not entries:
        return {"valid": False, "reason": "no_lineage_entries", "entries_checked": 0}
    issues: list[str] = []
    entry_map: dict[str, CommercialModelLineage] = {str(e.id): e for e in entries}
    for entry in entries:
        if entry.parent_lineage_id:
            parent = entry_map.get(str(entry.parent_lineage_id))
            if not parent:
                issues.append("orphan_parent:" + str(entry.parent_lineage_id))
            elif parent.depth != entry.depth - 1:
                issues.append("depth_mismatch:" + str(entry.id))
        if entry.predecessor_hash and not entry.artifact_hash:
            issues.append("missing_artifact_hash:" + str(entry.id))
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "entries_checked": len(entries),
        "max_depth": max((e.depth for e in entries), default=-1),
    }


async def get_lineage_ancestors(
    db: AsyncSession,
    lineage_id: UUID,
) -> list[CommercialModelLineage]:
    entry = await db.get(CommercialModelLineage, lineage_id)
    if not entry:
        return []
    ancestors: list[CommercialModelLineage] = []
    current = entry
    visited: set[str] = set()
    while current and current.parent_lineage_id and str(current.parent_lineage_id) not in visited:
        visited.add(str(current.parent_lineage_id))
        parent = await db.get(CommercialModelLineage, current.parent_lineage_id)
        if parent:
            ancestors.append(parent)
            current = parent
        else:
            break
    return ancestors


async def verify_provenance_chain(
    db: AsyncSession,
    lifecycle_record_id: UUID,
) -> dict[str, Any]:
    dag = await get_lineage_dag(db, lifecycle_record_id)
    if not dag["nodes"]:
        return {"valid": False, "reason": "no_lineage", "chain_length": 0}
    from app.models.commercial_model_lifecycle import CommercialModelLifecycleRecord
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        return {"valid": False, "reason": "lifecycle_record_not_found", "chain_length": dag["total_entries"]}
    provenance_linked = record.provenance_id is not None
    chain_length = 0
    for node in dag["nodes"]:
        if node.get("artifact_hash"):
            chain_length += 1
    return {
        "valid": provenance_linked and chain_length > 0,
        "provenance_linked": provenance_linked,
        "chain_length": chain_length,
        "total_nodes": dag["total_entries"],
        "max_depth": dag["depth"],
    }


async def list_lineage_entries(
    db: AsyncSession,
    *,
    lifecycle_record_id: UUID | None = None,
    limit: int = 100,
) -> list[CommercialModelLineage]:
    stmt = select(CommercialModelLineage).order_by(desc(CommercialModelLineage.created_at))
    if lifecycle_record_id:
        stmt = stmt.where(CommercialModelLineage.lifecycle_record_id == lifecycle_record_id)
    stmt = stmt.limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return result.scalars().all()


def serialize_lineage_entry(
    entry: CommercialModelLineage,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload({
        "id": str(entry.id),
        "lifecycle_record_id": str(entry.lifecycle_record_id),
        "parent_lineage_id": str(entry.parent_lineage_id) if entry.parent_lineage_id else None,
        "source_type": entry.source_type,
        "source_ref": entry.source_ref,
        "source_cluster_id": entry.source_cluster_id,
        "derivation_method": entry.derivation_method,
        "artifact_hash": _short(entry.artifact_hash),
        "predecessor_hash": _short(entry.predecessor_hash),
        "depth": entry.depth,
        "provenance_id": str(entry.provenance_id) if entry.provenance_id else None,
        "created_at": entry.created_at.isoformat(),
    })
