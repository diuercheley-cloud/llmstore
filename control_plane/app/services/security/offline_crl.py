from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_encryption import CommercialTenantEncryptionKey
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.models.commercial.commercial_governance_federation import (
    CommercialGovernanceFederationPeer,
)
from app.models.commercial.commercial_model_supply_chain import (
    CommercialModelProvenanceAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.models.commercial.commercial_sovereign_governance import (
    CommercialAirgapSyncPackage,
    CommercialOfflineRevocationList,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _crl_signature(payload: dict[str, Any]) -> str:
    settings = get_settings()
    secret = (
        settings.commercial_governance_federation_shared_token
        or settings.commercial_tenant_encryption_master_key
        or settings.admin_token
    )
    return hmac.new(
        secret.encode("utf-8"), _canonical_json(payload).encode("utf-8"), hashlib.sha256
    ).hexdigest()


async def create_offline_crl(
    db: AsyncSession,
    *,
    crl_version: str,
    revoked_key_fingerprints_json: list[str] | None = None,
    revoked_bundle_hashes_json: list[str] | None = None,
    revoked_peer_ids_json: list[str] | None = None,
    reason: str | None = None,
    expires_at: datetime | None = None,
) -> CommercialOfflineRevocationList:
    payload = sanitize_report_payload(
        {
            "crl_version": crl_version,
            "revoked_key_fingerprints_json": revoked_key_fingerprints_json or [],
            "revoked_bundle_hashes_json": revoked_bundle_hashes_json or [],
            "revoked_peer_ids_json": revoked_peer_ids_json or [],
            "reason": reason,
        }
    )
    manifest_hash = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    item = CommercialOfflineRevocationList(
        crl_version=crl_version,
        revoked_key_fingerprints_json=payload["revoked_key_fingerprints_json"],
        revoked_bundle_hashes_json=payload["revoked_bundle_hashes_json"],
        revoked_peer_ids_json=payload["revoked_peer_ids_json"],
        reason=payload.get("reason"),
        manifest_hash=manifest_hash,
        signature=_crl_signature({**payload, "manifest_hash": manifest_hash}),
        expires_at=expires_at,
    )
    db.add(item)
    await db.flush()
    return item


async def verify_offline_crl(crl: CommercialOfflineRevocationList) -> bool:
    payload = {
        "crl_version": crl.crl_version,
        "revoked_key_fingerprints_json": crl.revoked_key_fingerprints_json or [],
        "revoked_bundle_hashes_json": crl.revoked_bundle_hashes_json or [],
        "revoked_peer_ids_json": crl.revoked_peer_ids_json or [],
        "reason": crl.reason,
        "manifest_hash": crl.manifest_hash,
    }
    expected_hash = hashlib.sha256(
        _canonical_json({k: v for k, v in payload.items() if k != "manifest_hash"}).encode("utf-8")
    ).hexdigest()
    if expected_hash != crl.manifest_hash:
        return False
    return hmac.compare_digest(crl.signature, _crl_signature(payload))


async def apply_offline_crl(db: AsyncSession, crl_id) -> dict[str, int]:
    from app.services.models.signed_model_registry import revoke_model

    crl = await db.get(CommercialOfflineRevocationList, crl_id)
    if not crl:
        raise ValueError("CRL not found")
    if not await verify_offline_crl(crl):
        raise ValueError("Invalid offline CRL signature")

    key_count = 0
    for fingerprint in crl.revoked_key_fingerprints_json or []:
        rows = await db.execute(
            select(CommercialTenantEncryptionKey).where(
                CommercialTenantEncryptionKey.key_fingerprint == fingerprint
            )
        )
        for key in rows.scalars().all():
            key.key_status = "revoked"
            key_count += 1

    bundle_count = 0
    for bundle_hash in crl.revoked_bundle_hashes_json or []:
        registry_filters = [
            CommercialSignedModelRegistryEntry.manifest_hash == bundle_hash,
            CommercialSignedModelRegistryEntry.checksum_sha256 == bundle_hash,
        ]
        try:
            registry_filters.append(
                CommercialSignedModelRegistryEntry.id == uuid.UUID(str(bundle_hash))
            )
        except (ValueError, TypeError, AttributeError):
            pass
        rows = await db.execute(
            select(CommercialPolicyBundle).where(
                CommercialPolicyBundle.immutable_hash == bundle_hash
            )
        )
        for bundle in rows.scalars().all():
            bundle.status = "deprecated"
            bundle_count += 1
        package_rows = await db.execute(
            select(CommercialAirgapSyncPackage).where(
                CommercialAirgapSyncPackage.manifest_hash == bundle_hash
            )
        )
        for package in package_rows.scalars().all():
            package.status = "rejected"
        model_rows = await db.execute(
            select(CommercialSignedModelRegistryEntry).where(or_(*registry_filters))
        )
        for entry in model_rows.scalars().all():
            await revoke_model(
                db,
                entry_id=entry.id,
                reason=f"revoked by offline CRL {crl.crl_version}",
                revocation_type="crl",
                revoked_by="offline_crl",
            )
            bundle_count += 1

    peer_count = 0
    for peer_id in crl.revoked_peer_ids_json or []:
        rows = await db.execute(
            select(CommercialGovernanceFederationPeer).where(
                CommercialGovernanceFederationPeer.peer_cluster_id == peer_id
            )
        )
        for peer in rows.scalars().all():
            peer.status = "disabled"
            peer_count += 1
        model_rows = await db.execute(
            select(CommercialSignedModelRegistryEntry)
            .join(
                CommercialModelProvenanceAttestation,
                CommercialSignedModelRegistryEntry.provenance_id
                == CommercialModelProvenanceAttestation.id,
            )
            .where(CommercialModelProvenanceAttestation.source_cluster_id == peer_id)
        )
        for entry in model_rows.scalars().all():
            await revoke_model(
                db,
                entry_id=entry.id,
                reason=f"source peer revoked by offline CRL {crl.crl_version}",
                revocation_type="crl",
                revoked_by="offline_crl",
            )

    await db.flush()
    return {"revoked_keys": key_count, "revoked_bundles": bundle_count, "revoked_peers": peer_count}


async def _active_crls(db: AsyncSession) -> list[CommercialOfflineRevocationList]:
    rows = await db.execute(
        select(CommercialOfflineRevocationList).order_by(
            CommercialOfflineRevocationList.created_at.desc()
        )
    )
    now = utc_now()
    return [
        item for item in rows.scalars().all() if item.expires_at is None or item.expires_at >= now
    ]


async def is_key_revoked(db: AsyncSession, key_fingerprint: str | None) -> bool:
    if not key_fingerprint:
        return False
    for crl in await _active_crls(db):
        if key_fingerprint in (crl.revoked_key_fingerprints_json or []):
            return True
    return False


async def is_bundle_revoked(db: AsyncSession, bundle_hash: str | None) -> bool:
    if not bundle_hash:
        return False
    for crl in await _active_crls(db):
        if bundle_hash in (crl.revoked_bundle_hashes_json or []):
            return True
    return False


async def is_peer_revoked(db: AsyncSession, peer_id: str | None) -> bool:
    if not peer_id:
        return False
    for crl in await _active_crls(db):
        if peer_id in (crl.revoked_peer_ids_json or []):
            return True
    return False
