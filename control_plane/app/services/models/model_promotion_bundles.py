from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.core.time import utc_now
from app.models.core.admin_action_log import AdminActionLog
from app.models.commercial.commercial_model_supply_chain import (
    CommercialModelPromotionBundle,
    CommercialSignedModelRegistryEntry,
)
from app.services.models.model_provenance import create_provenance_attestation
from app.services.models.signed_model_registry import (
    get_provenance_entry,
    register_model_manifest,
    sign_model_manifest,
    verify_model_signature,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.offline_crl import is_bundle_revoked, is_peer_revoked
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _bundle_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


async def _log_bundle_audit(
    db: AsyncSession,
    *,
    action: str,
    status: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        AdminActionLog(
            action=action,
            admin_role="super_admin",
            payload_json=sanitize_report_payload(payload),
            result_json={},
            status=status,
        )
    )
    await db.flush()


async def create_model_promotion_bundle(
    db: AsyncSession,
    *,
    bundle_name: str,
    registry_entry_id: UUID,
    source_cluster_id: str | None = None,
    target_cluster_id: str | None = None,
    include_signature: bool = True,
) -> CommercialModelPromotionBundle:
    entry = await db.get(CommercialSignedModelRegistryEntry, registry_entry_id)
    if not entry:
        raise ValueError("Registry entry not found")
    provenance = await get_provenance_entry(db, entry.provenance_id)
    manifest = sanitize_report_payload(
        {
            "bundle_name": bundle_name,
            "source_cluster_id": source_cluster_id,
            "target_cluster_id": target_cluster_id,
            "model": {
                "model_name": entry.model_name,
                "model_alias": entry.model_alias,
                "model_version": entry.model_version,
                "provider": entry.provider,
                "model_format": entry.model_format,
                "checksum_sha256": entry.checksum_sha256,
                "manifest_hash": entry.manifest_hash,
                "signature": entry.signature,
                "tenant_scope_json": entry.tenant_scope_json,
            },
            "provenance": {
                "source_type": provenance.source_type if provenance else None,
                "source_uri": provenance.source_uri if provenance else None,
                "source_cluster_id": provenance.source_cluster_id if provenance else None,
                "import_method": provenance.import_method if provenance else None,
                "artifact_hash": provenance.artifact_hash if provenance else None,
                "evidence_json": provenance.evidence_json if provenance else {},
            },
            "chain_of_custody": provenance.chain_of_custody_json if provenance else None,
        }
    )
    manifest_hash = _bundle_manifest_hash(manifest)
    manifest["manifest_hash"] = manifest_hash
    signature = await sign_model_manifest(manifest) if include_signature else None
    bundle = CommercialModelPromotionBundle(
        bundle_name=bundle_name,
        source_cluster_id=source_cluster_id,
        target_cluster_id=target_cluster_id,
        manifest_json=manifest,
        manifest_hash=manifest_hash,
        signature=signature,
        status="created",
    )
    db.add(bundle)
    await db.flush()
    return bundle


async def verify_model_promotion_bundle(
    db: AsyncSession,
    bundle: CommercialModelPromotionBundle,
) -> dict[str, Any]:
    manifest = bundle.manifest_json or {}
    expected_hash = _bundle_manifest_hash(manifest)
    if manifest.get("manifest_hash") != expected_hash or bundle.manifest_hash != expected_hash:
        bundle.status = "rejected"
        await db.flush()
        return {"valid": False, "reason": "manifest_hash_mismatch"}
    if bundle.signature and not await verify_model_signature(manifest, bundle.signature):
        bundle.status = "rejected"
        await db.flush()
        return {"valid": False, "reason": "invalid_signature"}
    model = manifest.get("model") or {}
    provenance = manifest.get("provenance") or {}
    if not model.get("checksum_sha256") or not model.get("manifest_hash"):
        return {"valid": False, "reason": "missing_model_checksum_or_manifest"}
    if not provenance.get("artifact_hash"):
        return {"valid": False, "reason": "missing_provenance"}
    if await is_bundle_revoked(db, model.get("checksum_sha256")) or await is_bundle_revoked(db, model.get("manifest_hash")):
        bundle.status = "rejected"
        await db.flush()
        return {"valid": False, "reason": "revoked_by_offline_crl"}
    peer_id = provenance.get("source_cluster_id") or manifest.get("source_cluster_id")
    if await is_peer_revoked(db, peer_id):
        bundle.status = "rejected"
        await db.flush()
        return {"valid": False, "reason": "source_peer_revoked"}
    bundle.status = "verified"
    await db.flush()
    return {"valid": True, "manifest_hash": expected_hash}


async def promote_model_from_bundle(
    db: AsyncSession,
    bundle_id: UUID,
    *,
    imported_by: str | None = None,
) -> CommercialSignedModelRegistryEntry:
    bundle = await db.get(CommercialModelPromotionBundle, bundle_id)
    if not bundle:
        raise ValueError("Bundle not found")
    verification = await verify_model_promotion_bundle(db, bundle)
    if not verification["valid"]:
        raise ValueError(verification["reason"])
    manifest = bundle.manifest_json or {}
    provenance_manifest = manifest.get("provenance") or {}
    provenance = await create_provenance_attestation(
        db,
        source_type=provenance_manifest.get("source_type") or "airgap",
        source_uri=provenance_manifest.get("source_uri"),
        source_cluster_id=provenance_manifest.get("source_cluster_id") or bundle.source_cluster_id,
        imported_by=imported_by,
        import_method="airgap",
        artifact_hash=provenance_manifest.get("artifact_hash") or manifest.get("manifest_hash"),
        evidence_json=provenance_manifest.get("evidence_json") or {},
        chain_of_custody_json=manifest.get("chain_of_custody"),
    )
    model = manifest.get("model") or {}
    entry = await register_model_manifest(
        db,
        model_name=model.get("model_name"),
        model_alias=model.get("model_alias"),
        model_version=model.get("model_version"),
        provider=model.get("provider"),
        model_format=model.get("model_format") or "other",
        checksum_sha256=model.get("checksum_sha256"),
        signature=model.get("signature"),
        provenance_id=provenance.id,
        tenant_scope_json=model.get("tenant_scope_json"),
        trust_state="pending",
    )
    bundle.status = "promoted"
    bundle.promoted_at = utc_now()
    await _log_bundle_audit(
        db,
        action="bundle_promoted",
        status="success",
        payload={"bundle_id": str(bundle.id), "registry_entry_id": str(entry.id), "manifest_hash": bundle.manifest_hash},
    )
    await db.flush()
    return entry


async def reject_model_bundle(
    db: AsyncSession,
    bundle_id: UUID,
    *,
    reason: str,
) -> CommercialModelPromotionBundle:
    bundle = await db.get(CommercialModelPromotionBundle, bundle_id)
    if not bundle:
        raise ValueError("Bundle not found")
    bundle.status = "rejected"
    await _log_bundle_audit(
        db,
        action="bundle_rejected",
        status="success",
        payload={"bundle_id": str(bundle.id), "reason": reason},
    )
    await db.flush()
    return bundle


async def list_bundles(db: AsyncSession) -> list[CommercialModelPromotionBundle]:
    result = await db.execute(
        select(CommercialModelPromotionBundle).order_by(desc(CommercialModelPromotionBundle.created_at))
    )
    return result.scalars().all()
