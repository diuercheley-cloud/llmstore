from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_sovereign_governance import CommercialAirgapSyncPackage
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.local_aead import AESGCM
from app.services.security.offline_crl import is_bundle_revoked, is_key_revoked
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _hash_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    return _hash_payload(payload)


def _sign_bytes(payload: bytes) -> str:
    settings = get_settings()
    secret = (
        settings.commercial_governance_federation_shared_token
        or settings.commercial_tenant_encryption_master_key
        or settings.admin_token
    )
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _encrypt_payload(payload: dict[str, Any]) -> str:
    settings = get_settings()
    key = hashlib.sha256(settings.commercial_tenant_encryption_master_key.encode("utf-8")).digest()
    aesgcm = AESGCM(key)
    nonce = hashlib.sha256(_canonical_json(payload).encode("utf-8")).digest()[:12]
    ciphertext = aesgcm.encrypt(nonce, _canonical_json(payload).encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def _normalize_chain(chain_of_custody: dict[str, Any] | None) -> dict[str, Any]:
    sanitized = sanitize_report_payload(chain_of_custody or {})
    events = sanitized.get("events")
    if not isinstance(events, list):
        events = []
    sanitized["events"] = events
    return sanitized


def _requires_encryption(classification: str | None) -> bool:
    settings = get_settings()
    return bool(
        settings.commercial_airgap_require_encryption or classification == "sovereign_restricted"
    )


def _requires_signature(classification: str | None) -> bool:
    settings = get_settings()
    return bool(
        settings.commercial_airgap_require_signature or classification == "sovereign_restricted"
    )


async def sign_airgap_manifest(manifest: dict[str, Any]) -> str:
    return _sign_bytes(_canonical_json(manifest).encode("utf-8"))


async def verify_airgap_manifest(
    db: AsyncSession,
    package_bundle: dict[str, Any],
) -> dict[str, Any]:
    files = package_bundle.get("files") or {}
    manifest = files.get("manifest.json") or package_bundle.get("manifest")
    signature = files.get("signature.txt") or package_bundle.get("signature")
    checksums = files.get("checksums.txt", "")
    if not manifest or not signature:
        return {"valid": False, "reason": "Missing manifest or signature"}

    expected_hash = _manifest_hash(manifest)
    if manifest.get("manifest_hash") != expected_hash:
        return {"valid": False, "reason": "Manifest hash mismatch"}

    if _requires_signature(manifest.get("classification")):
        expected_sig = await sign_airgap_manifest(manifest)
        if signature != expected_sig:
            return {"valid": False, "reason": "Invalid manifest signature"}

    payload_name = "payload.enc" if "payload.enc" in files else "payload.json"
    payload_value = files.get(payload_name)
    if not payload_value:
        return {"valid": False, "reason": "Missing payload"}

    if checksums:
        checksum_lines = dict(
            line.split("  ", 1) for line in checksums.splitlines() if "  " in line
        )
        for name, value in files.items():
            expected = checksum_lines.get(name)
            if expected and hashlib.sha256(str(value).encode("utf-8")).hexdigest() != expected:
                return {"valid": False, "reason": f"Checksum mismatch for {name}"}

    chain = files.get("chain_of_custody.json") or {}
    chain_ok = await validate_chain_of_custody(chain)
    if not chain_ok["valid"]:
        return chain_ok

    if await is_bundle_revoked(db, expected_hash):
        return {"valid": False, "reason": "Package manifest revoked by offline CRL"}

    encryption_key_id = manifest.get("encryption_key_id")
    if encryption_key_id and await is_key_revoked(db, manifest.get("key_fingerprint")):
        return {"valid": False, "reason": "Encryption key revoked by offline CRL"}

    return {"valid": True, "manifest_hash": expected_hash, "payload_name": payload_name}


async def validate_chain_of_custody(chain_of_custody: dict[str, Any]) -> dict[str, Any]:
    sanitized = _normalize_chain(chain_of_custody)
    events = sanitized.get("events", [])
    if not events:
        return {"valid": False, "reason": "Chain of custody events required"}
    for event in events:
        if not isinstance(event, dict):
            return {"valid": False, "reason": "Invalid chain of custody entry"}
        if not event.get("actor") or not event.get("action") or not event.get("timestamp"):
            return {"valid": False, "reason": "Incomplete chain of custody entry"}
    return {"valid": True, "events": len(events)}


async def create_airgap_package(
    db: AsyncSession,
    *,
    package_type: str,
    payload: dict[str, Any],
    source_cluster_id: str,
    target_cluster_id: str | None = None,
    package_version: str = "1.0",
    classification: str | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
    encryption_key_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> CommercialAirgapSyncPackage:
    settings = get_settings()
    if not settings.commercial_airgap_sync_enabled:
        raise ValueError("Airgap synchronization is disabled")

    sanitized_payload = sanitize_report_payload(payload)
    chain = _normalize_chain(chain_of_custody_json)
    chain_check = await validate_chain_of_custody(chain)
    if not chain_check["valid"]:
        raise ValueError(chain_check["reason"])

    manifest = {
        "package_type": package_type,
        "source_cluster_id": source_cluster_id,
        "target_cluster_id": target_cluster_id,
        "package_version": package_version,
        "classification": classification or "internal",
        "created_at": utc_now().isoformat(),
        "chain_of_custody_hash": _hash_payload(chain),
        "payload_hash": _hash_payload(sanitized_payload),
        "encryption_key_id": str(encryption_key_id) if encryption_key_id else None,
    }
    manifest_hash = _manifest_hash(manifest)
    manifest["manifest_hash"] = manifest_hash
    signature = await sign_airgap_manifest(manifest)

    package = CommercialAirgapSyncPackage(
        package_type=package_type,
        source_cluster_id=source_cluster_id,
        target_cluster_id=target_cluster_id,
        package_version=package_version,
        manifest_hash=manifest_hash,
        signature=signature,
        encryption_key_id=encryption_key_id,
        status="created",
        file_ref=f"airgap://{source_cluster_id}/{manifest_hash[:16]}",
        chain_of_custody_json=chain,
        expires_at=expires_at or (utc_now() + timedelta(days=30)),
    )
    db.add(package)
    await db.flush()
    return package


async def export_airgap_package(
    db: AsyncSession,
    package_id: uuid.UUID,
    *,
    payload: dict[str, Any],
    classification: str | None = None,
    key_fingerprint: str | None = None,
) -> dict[str, Any]:
    package = await db.get(CommercialAirgapSyncPackage, package_id)
    if not package:
        raise ValueError("Package not found")

    manifest = {
        "package_id": str(package.id),
        "package_type": package.package_type,
        "source_cluster_id": package.source_cluster_id,
        "target_cluster_id": package.target_cluster_id,
        "package_version": package.package_version,
        "classification": classification or "internal",
        "created_at": package.created_at.isoformat(),
        "expires_at": package.expires_at.isoformat() if package.expires_at else None,
        "chain_of_custody_hash": _hash_payload(package.chain_of_custody_json),
        "payload_hash": _hash_payload(sanitize_report_payload(payload)),
        "encryption_key_id": str(package.encryption_key_id) if package.encryption_key_id else None,
        "key_fingerprint": key_fingerprint,
    }
    manifest["manifest_hash"] = _manifest_hash(manifest)
    signature = await sign_airgap_manifest(manifest)

    use_encryption = _requires_encryption(classification)
    files: dict[str, Any] = {
        "manifest.json": manifest,
        "signature.txt": signature,
        "chain_of_custody.json": package.chain_of_custody_json,
    }
    if use_encryption:
        files["payload.enc"] = _encrypt_payload(sanitize_report_payload(payload))
    else:
        files["payload.json"] = sanitize_report_payload(payload)
    checksum_lines = [
        f"{hashlib.sha256(str(value).encode('utf-8')).hexdigest()}  {name}"
        for name, value in files.items()
    ]
    files["checksums.txt"] = "\n".join(checksum_lines)

    package.manifest_hash = manifest["manifest_hash"]
    package.signature = signature
    package.status = "exported"
    await db.flush()
    return {
        "package_id": str(package.id),
        "files": files,
        "dry_run": get_settings().commercial_airgap_sync_mode == "dry_run",
    }


async def import_airgap_package(
    db: AsyncSession,
    package_bundle: dict[str, Any],
) -> CommercialAirgapSyncPackage:
    verification = await verify_airgap_manifest(db, package_bundle)
    manifest = (
        (package_bundle.get("files") or {}).get("manifest.json")
        or package_bundle.get("manifest")
        or {}
    )
    package_id = manifest.get("package_id")
    package = (
        await db.get(CommercialAirgapSyncPackage, uuid.UUID(package_id)) if package_id else None
    )
    if package is None:
        package = CommercialAirgapSyncPackage(
            package_type=manifest.get("package_type", "policy_bundle"),
            source_cluster_id=manifest.get("source_cluster_id", "unknown"),
            target_cluster_id=manifest.get("target_cluster_id"),
            package_version=manifest.get("package_version", "1.0"),
            manifest_hash=manifest.get("manifest_hash", ""),
            signature=(package_bundle.get("files") or {}).get("signature.txt", ""),
            encryption_key_id=uuid.UUID(manifest["encryption_key_id"])
            if manifest.get("encryption_key_id")
            else None,
            status="created",
            file_ref=f"airgap://imported/{manifest.get('manifest_hash', '')[:16]}",
            chain_of_custody_json=_normalize_chain(
                (package_bundle.get("files") or {}).get("chain_of_custody.json")
            ),
        )
        db.add(package)
        await db.flush()

    if not verification["valid"]:
        package.status = "rejected"
        package.imported_at = utc_now()
        await db.flush()
        raise ValueError(verification["reason"])

    package.status = "verified"
    package.imported_at = utc_now()
    await db.flush()
    return package


async def reject_package(
    db: AsyncSession,
    package_id: uuid.UUID,
    *,
    reason: str,
) -> CommercialAirgapSyncPackage:
    package = await db.get(CommercialAirgapSyncPackage, package_id)
    if not package:
        raise ValueError("Package not found")
    chain = _normalize_chain(package.chain_of_custody_json)
    chain["events"].append(
        {"actor": "admin", "action": "reject", "timestamp": utc_now().isoformat(), "reason": reason}
    )
    package.chain_of_custody_json = chain
    package.status = "rejected"
    await db.flush()
    return package
