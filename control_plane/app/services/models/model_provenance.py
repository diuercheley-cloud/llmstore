from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.models.commercial_model_supply_chain import (
    CommercialModelProvenanceAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.services.governance.airgap_sync import validate_chain_of_custody as validate_airgap_chain
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


async def validate_chain_of_custody(chain_of_custody_json: dict[str, Any] | None) -> dict[str, Any]:
    if not chain_of_custody_json:
        return {"valid": True, "events": 0, "reason": "no_chain_provided"}
    return await validate_airgap_chain(chain_of_custody_json)


async def create_provenance_attestation(
    db: AsyncSession,
    *,
    source_type: str,
    source_uri: str | None = None,
    source_cluster_id: str | None = None,
    imported_by: str | None = None,
    import_method: str,
    artifact_hash: str,
    evidence_json: dict[str, Any] | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
) -> CommercialModelProvenanceAttestation:
    sanitized_evidence = sanitize_report_payload(evidence_json or {})
    sanitized_chain = sanitize_report_payload(chain_of_custody_json) if chain_of_custody_json is not None else None
    chain_validation = await validate_chain_of_custody(sanitized_chain)
    if not chain_validation["valid"]:
        raise ValueError(chain_validation["reason"])
    artifact_hash = artifact_hash or hashlib.sha256(_canonical_json(sanitized_evidence).encode("utf-8")).hexdigest()
    item = CommercialModelProvenanceAttestation(
        source_type=str(source_type),
        source_uri=str(source_uri)[:512] if source_uri else None,
        source_cluster_id=str(source_cluster_id)[:255] if source_cluster_id else None,
        imported_by=str(imported_by)[:255] if imported_by else None,
        import_method=str(import_method),
        artifact_hash=artifact_hash,
        evidence_json=sanitized_evidence,
        chain_of_custody_json=sanitized_chain,
    )
    db.add(item)
    await db.flush()
    return item


async def link_provenance_to_model(
    db: AsyncSession,
    *,
    registry_entry_id: UUID,
    provenance_id: UUID,
) -> CommercialSignedModelRegistryEntry:
    entry = await db.get(CommercialSignedModelRegistryEntry, registry_entry_id)
    if not entry:
        raise ValueError("Registry entry not found")
    provenance = await db.get(CommercialModelProvenanceAttestation, provenance_id)
    if not provenance:
        raise ValueError("Provenance attestation not found")
    entry.provenance_id = provenance.id
    await db.flush()
    return entry


async def summarize_model_provenance(
    db: AsyncSession,
    provenance_id: UUID | None,
) -> dict[str, Any] | None:
    if provenance_id is None:
        return None
    provenance = await db.get(CommercialModelProvenanceAttestation, provenance_id)
    if provenance is None:
        return None
    chain = provenance.chain_of_custody_json or {}
    events = chain.get("events") if isinstance(chain, dict) else []
    return {
        "id": str(provenance.id),
        "source_type": provenance.source_type,
        "source_uri": provenance.source_uri,
        "source_cluster_id": provenance.source_cluster_id,
        "import_method": provenance.import_method,
        "artifact_hash": provenance.artifact_hash,
        "evidence_keys": sorted((provenance.evidence_json or {}).keys()),
        "chain_of_custody_events": len(events) if isinstance(events, list) else 0,
        "created_at": provenance.created_at.isoformat(),
    }
